import json
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Exists, OuterRef
from .models import Draft, DraftOrder, Pick, Player, TradeOffer


@login_required
def draft_room(request, draft_id):
    draft = get_object_or_404(Draft, id=draft_id)

    if request.method == 'POST' and request.user.is_superuser:
        action = request.POST.get('action')
        if action == 'reset':
            Pick.objects.filter(draft=draft).delete()
            draft.current_pick_number = 1
            draft.save()
            return redirect('draft_room', draft_id=draft.id)
        elif action == 'skip':
            draft.current_pick_number += 1
            draft.save()
            return redirect('draft_room', draft_id=draft.id)

    picks = Pick.objects.filter(draft=draft).order_by('-pick_number')

    total_presidents = DraftOrder.objects.filter(draft=draft).count()
    if total_presidents == 0:
        return render(request, 'draftapp/draft_room.html', {'error': 'Ordem não configurada.'})

    current_round = (draft.current_pick_number - 1) // total_presidents
    pick_in_round = ((draft.current_pick_number - 1) % total_presidents) + 1

    if current_round % 2 == 0:
        current_turn_index = pick_in_round
    else:
        current_turn_index = total_presidents - pick_in_round + 1

    current_turn_order = get_object_or_404(DraftOrder, draft=draft, pick_order=current_turn_index)
    is_my_turn = (request.user == current_turn_order.president)

    user_draft_order = DraftOrder.objects.filter(draft=draft, president=request.user).first()
    missing_pick_numbers = []

    if user_draft_order:
        expected_picks = []
        for p in range(1, draft.current_pick_number):
            c_round = (p - 1) // total_presidents
            p_in_round = ((p - 1) % total_presidents) + 1
            owner_order = p_in_round if c_round % 2 == 0 else (total_presidents - p_in_round + 1)

            if owner_order == user_draft_order.pick_order:
                expected_picks.append(p)

        actual_picks = Pick.objects.filter(draft=draft, president=request.user).values_list('pick_number', flat=True)
        missing_pick_numbers = sorted(list(set(expected_picks) - set(actual_picks)))

    has_late_picks = len(missing_pick_numbers) > 0
    can_pick = is_my_turn or has_late_picks or request.user.is_superuser

    if request.method == 'POST' and can_pick and not request.POST.get('action'):
        player_id = request.POST.get('player_id')
        player = get_object_or_404(Player, id=player_id)

        if not Pick.objects.filter(draft=draft, player=player).exists():
            if is_my_turn:
                pick_pres = current_turn_order.president
                assign_num = draft.current_pick_number
                adv_clock = True
            elif has_late_picks:
                pick_pres = request.user
                assign_num = missing_pick_numbers[0]
                adv_clock = False
            elif request.user.is_superuser:
                pick_pres = current_turn_order.president
                assign_num = draft.current_pick_number
                adv_clock = True

            Pick.objects.create(draft=draft, president=pick_pres, player=player, pick_number=assign_num)

            if adv_clock:
                draft.current_pick_number += 1
                draft.save()
            return redirect('draft_room', draft_id=draft.id)

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

    # AJAX: Salvar Posição no Campo
    if request.method == 'POST' and request.content_type == 'application/json':
        try:
            data = json.loads(request.body)
            if data.get('action') == 'update_lineup':
                pick_id = data.get('pick_id')
                slot_id = data.get('slot_id')
                pick = get_object_or_404(Pick, id=pick_id, draft=draft)
                if request.user == pick.president or request.user.is_superuser:
                    pick.lineup_slot = slot_id if slot_id != 'bench' else None
                    pick.save()
                    return JsonResponse({'status': 'ok'})
                else:
                    return JsonResponse({'status': 'forbidden'}, status=403)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

    presidents_in_draft = [order.president for order in
                           DraftOrder.objects.filter(draft=draft).select_related('president').order_by('pick_order')]

    selected_president_id = request.GET.get('president_id')
    if not selected_president_id and presidents_in_draft:
        selected_president_id = presidents_in_draft[0].id
    elif selected_president_id:
        selected_president_id = int(selected_president_id)

    # ==========================================================
    # SISTEMA DE TROCAS (TRADE CENTER) E ADMIN
    # ==========================================================
    if request.method == 'POST' and not request.content_type == 'application/json':
        action = request.POST.get('action')

        # 1. Propor a Troca
        if action == 'propose_trade':
            offered_ids = request.POST.getlist('offered_picks')
            requested_ids = request.POST.getlist('requested_picks')
            if offered_ids and requested_ids:
                trade = TradeOffer.objects.create(draft=draft, proposer=request.user, target_id=selected_president_id)
                trade.offered_picks.set(offered_ids)
                trade.requested_picks.set(requested_ids)
            return redirect(f"{request.path}?president_id={selected_president_id}")

        # 2. Aceitar a Troca (Faz a magia de trocar os donos das cartas)
        elif action == 'accept_trade':
            trade_id = request.POST.get('trade_id')
            trade = get_object_or_404(TradeOffer, id=trade_id, target=request.user, status='PENDING')

            # Validação de segurança: Os jogadores ainda pertencem aos donos originais?
            valid = True
            for p in trade.offered_picks.all():
                if p.president != trade.proposer: valid = False
            for p in trade.requested_picks.all():
                if p.president != trade.target: valid = False

            if valid:
                for p in trade.offered_picks.all():
                    p.president = trade.target
                    p.lineup_slot = None  # Manda pro banco do novo dono
                    p.save()
                for p in trade.requested_picks.all():
                    p.president = trade.proposer
                    p.lineup_slot = None
                    p.save()
                trade.status = 'ACCEPTED'
            else:
                trade.status = 'CANCELED'  # Cancela automaticamente se alguém já foi trocado antes
            trade.save()
            return redirect(f"{request.path}?president_id={request.user.id}")

        # 3. Recusar Troca
        elif action == 'reject_trade':
            trade_id = request.POST.get('trade_id')
            trade = get_object_or_404(TradeOffer, id=trade_id, target=request.user)
            trade.status = 'REJECTED'
            trade.save()
            return redirect(f"{request.path}?president_id={request.user.id}")

        # 4. Cancelar Troca (Se o proponente desistir)
        elif action == 'cancel_trade':
            trade_id = request.POST.get('trade_id')
            trade = get_object_or_404(TradeOffer, id=trade_id, proposer=request.user)
            trade.status = 'CANCELED'
            trade.save()
            return redirect(f"{request.path}?president_id={selected_president_id}")

        # 5. Salvar Escalação (Fallback sem AJAX)
        elif action == 'save_lineup':
            for key, value in request.POST.items():
                if key.startswith('pick_'):
                    pick_id = key.split('_')[1]
                    try:
                        pick = Pick.objects.get(id=pick_id, draft=draft)
                        if request.user == pick.president or request.user.is_superuser:
                            pick.lineup_slot = value if value != 'bench' else None
                            pick.save()
                    except Pick.DoesNotExist:
                        pass
            return redirect(f"{request.path}?president_id={selected_president_id}")

        # 6. Admin Tools
        elif request.user.is_superuser:
            if action == 'delete_pick':
                Pick.objects.filter(id=request.POST.get('pick_id')).delete()
                if draft.current_pick_number > 1:
                    draft.current_pick_number -= 1
                    draft.save()
            elif action == 'add_pick':
                player = get_object_or_404(Player, id=request.POST.get('player_id'))
                if not Pick.objects.filter(draft=draft, player=player).exists():
                    Pick.objects.create(draft=draft, president_id=selected_president_id, player=player,
                                        pick_number=draft.current_pick_number)
                    draft.current_pick_number += 1
                    draft.save()
            return redirect(f"{request.path}?president_id={selected_president_id}")

    # Coleta de Dados para a Tela
    selected_picks = Pick.objects.filter(draft=draft, president_id=selected_president_id).order_by('-player__overall')
    my_picks = Pick.objects.filter(draft=draft, president=request.user).order_by(
        '-player__overall') if request.user.is_authenticated else []

    # Busca propostas de trocas ativas do usuário logado
    pending_received_trades = TradeOffer.objects.filter(draft=draft, target=request.user,
                                                        status='PENDING') if request.user.is_authenticated else []
    pending_sent_trades = TradeOffer.objects.filter(draft=draft, proposer=request.user,
                                                    status='PENDING') if request.user.is_authenticated else []

    available_players = []
    search_query = request.GET.get('q', '')
    if request.user.is_superuser:
        picked_ids = Pick.objects.filter(draft=draft).values_list('player_id', flat=True)
        if search_query:
            available_players = Player.objects.filter(version=draft.version, name__icontains=search_query).exclude(
                id__in=picked_ids).order_by('-overall')[:50]
        else:
            available_players = Player.objects.filter(version=draft.version).exclude(id__in=picked_ids).order_by(
                '-overall')[:20]

    context = {
        'draft': draft,
        'presidents': presidents_in_draft,
        'selected_president_id': selected_president_id,
        'selected_picks': selected_picks,
        'my_picks': my_picks,
        'pending_received_trades': pending_received_trades,
        'pending_sent_trades': pending_sent_trades,
        'available_players': available_players,
        'search_query': search_query,
    }
    return render(request, 'draftapp/teams.html', context)