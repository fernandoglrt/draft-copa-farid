from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Exists, OuterRef
from .models import Draft, DraftOrder, Pick, Player


@login_required
def draft_room(request, draft_id):
    draft = get_object_or_404(Draft, id=draft_id)

    # ==========================================================
    # BOTÃO DE PÂNICO: RESET DO DRAFT (Apenas Superuser)
    # ==========================================================
    if request.method == 'POST' and request.POST.get('action') == 'reset' and request.user.is_superuser:
        Pick.objects.filter(draft=draft).delete()  # Apaga todas as escolhas
        draft.current_pick_number = 1  # Volta o relógio pro 1
        draft.save()
        return redirect('draft_room', draft_id=draft.id)

    picks = Pick.objects.filter(draft=draft).order_by('-pick_number')

    total_presidents = DraftOrder.objects.filter(draft=draft).count()
    if total_presidents == 0:
        return render(request, 'draftapp/draft_room.html', {'error': 'Ordem não configurada.'})

    # ==========================================================
    # MATEMÁTICA DO SNAKE DRAFT (Bate no fundo e volta)
    # ==========================================================
    # Descobre em qual rodada estamos (0 = primeira, 1 = segunda, etc.)
    current_round = (draft.current_pick_number - 1) // total_presidents

    # Descobre a posição dentro da rodada (de 1 até o total de presidentes)
    pick_in_round = ((draft.current_pick_number - 1) % total_presidents) + 1

    # Rodadas Pares (0, 2, 4...) -> Ordem Normal (1, 2, 3... 16)
    if current_round % 2 == 0:
        current_turn_index = pick_in_round
    # Rodadas Ímpares (1, 3, 5...) -> Ordem Invertida (16, 15, 14... 1)
    else:
        current_turn_index = total_presidents - pick_in_round + 1
    # ==========================================================

    current_turn_order = get_object_or_404(DraftOrder, draft=draft, pick_order=current_turn_index)

    can_pick = (request.user == current_turn_order.president) or request.user.is_superuser

    # Lógica normal de fazer uma escolha
    if request.method == 'POST' and can_pick and not request.POST.get('action'):
        player_id = request.POST.get('player_id')
        player = get_object_or_404(Player, id=player_id)

        if not Pick.objects.filter(draft=draft, player=player).exists():
            Pick.objects.create(
                draft=draft, president=current_turn_order.president,
                player=player, pick_number=draft.current_pick_number
            )
            draft.current_pick_number += 1
            draft.save()
            return redirect('draft_room', draft_id=draft.id)

    picked_ids = picks.values_list('player_id', flat=True)

    # 1. Pega o texto que o usuário digitou na pesquisa (se houver)
    search_query = request.GET.get('q', '')

    # 2. Se ele digitou algo, o Django varre a base INTEIRA procurando aquele nome
    if search_query:
        available_top_players = Player.objects.filter(
            version=draft.version,
            name__icontains=search_query  # icontains ignora maiúsculas/minúsculas
        ).exclude(id__in=picked_ids).order_by('-overall')[:50]  # Traz os 50 melhores resultados

    # 3. Se a barra de pesquisa estiver vazia, mostra o Top 100 normal
    else:
        available_top_players = Player.objects.filter(
            version=draft.version
        ).exclude(id__in=picked_ids).order_by('-overall')[:100]

    context = {
        'draft': draft,
        'current_president': current_turn_order.president,
        'can_pick': can_pick,
        'picks': picks,
        'available_top_players': available_top_players,
        'search_query': search_query,  # Passa o termo pro HTML não esquecer o que foi digitado
    }
    return render(request, 'draftapp/draft_room.html', context)


@login_required
def scout_players(request, draft_id):
    draft = get_object_or_404(Draft, id=draft_id)
    picked_subquery = Pick.objects.filter(draft=draft, player=OuterRef('pk'))
    players = Player.objects.filter(version=draft.version).annotate(is_picked=Exists(picked_subquery))
    return render(request, 'draftapp/scout.html', {'players': players, 'draft': draft})