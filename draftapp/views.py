from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Exists, OuterRef
from .models import Draft, DraftOrder, Pick, Player


@login_required
@login_required
@login_required
def draft_room(request, draft_id):
    draft = get_object_or_404(Draft, id=draft_id)

    # ==========================================================
    # ZONA ADMIN: CONTROLE DO DRAFT (Resetar e Pular)
    # ==========================================================
    if request.method == 'POST' and request.user.is_superuser:
        action = request.POST.get('action')

        # Admin resetando tudo
        if action == 'reset':
            Pick.objects.filter(draft=draft).delete()
            draft.current_pick_number = 1
            draft.save()
            return redirect('draft_room', draft_id=draft.id)

        # Admin pulando a vez do presidente atual
        elif action == 'skip':
            draft.current_pick_number += 1
            draft.save()
            return redirect('draft_room', draft_id=draft.id)
    # ==========================================================

    picks = Pick.objects.filter(draft=draft).order_by('-pick_number')

    total_presidents = DraftOrder.objects.filter(draft=draft).count()
    if total_presidents == 0:
        return render(request, 'draftapp/draft_room.html', {'error': 'Ordem não configurada.'})

    # ==========================================================
    # MATEMÁTICA DO SNAKE DRAFT (Turno Atual)
    # ==========================================================
    current_round = (draft.current_pick_number - 1) // total_presidents
    pick_in_round = ((draft.current_pick_number - 1) % total_presidents) + 1

    if current_round % 2 == 0:
        current_turn_index = pick_in_round
    else:
        current_turn_index = total_presidents - pick_in_round + 1

    current_turn_order = get_object_or_404(DraftOrder, draft=draft, pick_order=current_turn_index)
    is_my_turn = (request.user == current_turn_order.president)

    # ==========================================================
    # MÁGICA DOS PICKS ATRASADOS (Retroativo)
    # ==========================================================
    user_draft_order = DraftOrder.objects.filter(draft=draft, president=request.user).first()
    missing_pick_numbers = []

    if user_draft_order:
        expected_picks = []
        # O sistema recalcula o dono de todos os picks passados para ver se o usuário perdeu algum
        for p in range(1, draft.current_pick_number):
            c_round = (p - 1) // total_presidents
            p_in_round = ((p - 1) % total_presidents) + 1
            owner_order = p_in_round if c_round % 2 == 0 else (total_presidents - p_in_round + 1)

            if owner_order == user_draft_order.pick_order:
                expected_picks.append(p)

        # Pega as escolhas que ele já fez de verdade
        actual_picks = Pick.objects.filter(draft=draft, president=request.user).values_list('pick_number', flat=True)
        # Se a matemática diz que ele devia ter o pick X e ele não tá no banco, é um pick atrasado!
        missing_pick_numbers = sorted(list(set(expected_picks) - set(actual_picks)))

    has_late_picks = len(missing_pick_numbers) > 0

    # Ele pode escolher se for a vez dele, se tiver atrasado, ou se for Admin
    can_pick = is_my_turn or has_late_picks or request.user.is_superuser

    # ==========================================================
    # EFETUANDO O DRAFT (Lógica Avançada)
    # ==========================================================
    if request.method == 'POST' and can_pick and not request.POST.get('action'):
        player_id = request.POST.get('player_id')
        player = get_object_or_404(Player, id=player_id)

        if not Pick.objects.filter(draft=draft, player=player).exists():
            # Define quem tá escolhendo e qual é o número do Pick
            if is_my_turn:
                pick_pres = current_turn_order.president
                assign_num = draft.current_pick_number
                adv_clock = True
            elif has_late_picks:
                pick_pres = request.user
                assign_num = missing_pick_numbers[0]  # Usa o exato número de pick que ficou para trás
                adv_clock = False  # Não avança o relógio geral, porque ele está recuperando uma falha
            elif request.user.is_superuser:
                pick_pres = current_turn_order.president
                assign_num = draft.current_pick_number
                adv_clock = True

            Pick.objects.create(
                draft=draft, president=pick_pres,
                player=player, pick_number=assign_num
            )

            if adv_clock:
                draft.current_pick_number += 1
                draft.save()
            return redirect('draft_room', draft_id=draft.id)

    # ==========================================================
    # FILTRO DE BUSCA GLOBAL
    # ==========================================================
    picked_ids = picks.values_list('player_id', flat=True)
    search_query = request.GET.get('q', '')

    if search_query:
        available_top_players = Player.objects.filter(version=draft.version, name__icontains=search_query).exclude(
            id__in=picked_ids).order_by('-overall')[:50]
    else:
        available_top_players = Player.objects.filter(version=draft.version).exclude(id__in=picked_ids).order_by(
            '-overall')[:100]

    context = {
        'draft': draft,
        'current_president': current_turn_order.president,
        'can_pick': can_pick,
        'is_my_turn': is_my_turn,
        'has_late_picks': has_late_picks,
        'missing_pick_count': len(missing_pick_numbers),
        'picks': picks,
        'available_top_players': available_top_players,
        'search_query': search_query,
    }
    return render(request, 'draftapp/draft_room.html', context)

@login_required
def scout_players(request, draft_id):
    draft = get_object_or_404(Draft, id=draft_id)
    picked_subquery = Pick.objects.filter(draft=draft, player=OuterRef('pk'))
    players = Player.objects.filter(version=draft.version).annotate(is_picked=Exists(picked_subquery))
    return render(request, 'draftapp/scout.html', {'players': players, 'draft': draft})


@login_required
def teams_view(request, draft_id):
    draft = get_object_or_404(Draft, id=draft_id)

    # Pega todos os presidentes que estão participando deste draft
    presidents_in_draft = [order.president for order in
                           DraftOrder.objects.filter(draft=draft).select_related('president').order_by('pick_order')]

    # Pega o presidente selecionado no filtro (ou o primeiro da lista por padrão)
    selected_president_id = request.GET.get('president_id')
    if not selected_president_id and presidents_in_draft:
        selected_president_id = presidents_in_draft[0].id
    elif selected_president_id:
        selected_president_id = int(selected_president_id)

    # ==========================================================
    # ZONA ADMIN (Adicionar ou Excluir Picks)
    # ==========================================================
    if request.method == 'POST' and request.user.is_superuser:
        action = request.POST.get('action')

        # Admin deletando um pick
        if action == 'delete_pick':
            pick_id = request.POST.get('pick_id')
            Pick.objects.filter(id=pick_id).delete()
            # Volta o relógio do draft em 1 para manter a ordem certa
            if draft.current_pick_number > 1:
                draft.current_pick_number -= 1
                draft.save()

        # Admin forçando a adição de um pick
        elif action == 'add_pick':
            player_id = request.POST.get('player_id')
            if player_id:
                player = get_object_or_404(Player, id=player_id)
                # Verifica se o jogador já não foi pego
                if not Pick.objects.filter(draft=draft, player=player).exists():
                    Pick.objects.create(
                        draft=draft,
                        president_id=selected_president_id,
                        player=player,
                        pick_number=draft.current_pick_number
                    )
                    draft.current_pick_number += 1
                    draft.save()

        # Recarrega a página mantendo o mesmo presidente selecionado
        return redirect(f"{request.path}?president_id={selected_president_id}")

    # ==========================================================

    # Carrega os jogadores do time selecionado (A linha que tinha sumido!)
    selected_picks = Pick.objects.filter(draft=draft, president_id=selected_president_id).order_by('pick_number')

    # ==========================================================
    # ZONA ADMIN - BUSCA DE JOGADORES EM TEMPO REAL
    # ==========================================================
    available_players = []
    search_query = request.GET.get('q', '')

    if request.user.is_superuser:
        picked_ids = Pick.objects.filter(draft=draft).values_list('player_id', flat=True)

        if search_query:
            # Se o admin digitou algo, varre a base inteira atrás do nome
            available_players = Player.objects.filter(
                version=draft.version,
                name__icontains=search_query
            ).exclude(id__in=picked_ids).order_by('-overall')[:50]
        else:
            # Se a busca estiver vazia, traz só os 20 melhores para não pesar
            available_players = Player.objects.filter(
                version=draft.version
            ).exclude(id__in=picked_ids).order_by('-overall')[:20]

    # Note que agora o context está alinhado corretamente na margem da função
    context = {
        'draft': draft,
        'presidents': presidents_in_draft,
        'selected_president_id': selected_president_id,
        'selected_picks': selected_picks,
        'available_players': available_players,
        'search_query': search_query,
    }
    return render(request, 'draftapp/teams.html', context)