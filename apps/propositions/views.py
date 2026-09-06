from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from apps.demandes.models import Demande

from .forms import EvaluationForm, PaiementForm, PropositionForm
from .models import Evaluation, Mission, Paiement, Proposition


@login_required
def soumettre_proposition(request, pk):
    demande = get_object_or_404(Demande, pk=pk)
    if request.user.role != 'prestataire':
        messages.error(request, 'Seul un prestataire peut soumettre une proposition.')
        return redirect('demandes:catalogue')
    if demande.statut not in (Demande.Statut.EN_COURS, Demande.Statut.EN_ATTENTE):
        messages.warning(request, 'Cette demande ne reçoit plus de propositions.')
        return redirect('demandes:detail_demande', pk=demande.pk)
    if request.method == 'POST':
        form = PropositionForm(request.POST)
        if form.is_valid():
            proposition = form.save(commit=False)
            proposition.demande = demande
            proposition.prestataire = request.user
            proposition.save()
            messages.success(request, 'Ta proposition a été envoyée au client.')
            return redirect('propositions:mes_propositions')
    else:
        form = PropositionForm()
    return render(request, 'propositions/soumettre.html', {'form': form, 'demande': demande})


@login_required
def mes_propositions(request):
    propositions = Proposition.objects.filter(prestataire=request.user).select_related('demande')
    return render(request, 'propositions/mes_propositions.html', {'propositions': propositions})


@login_required
def propositions_demande(request, pk):
    demande = get_object_or_404(Demande, pk=pk, client=request.user)
    propositions = demande.propositions.all().select_related('prestataire')
    return render(request, 'propositions/propositions_demande.html', {
        'demande': demande,
        'propositions': propositions,
    })


@login_required
def accepter_proposition(request, pk):
    proposition = get_object_or_404(Proposition, pk=pk)
    demande = proposition.demande
    has_mission = hasattr(demande, 'mission')
    if demande.client != request.user or has_mission:
        messages.error(request, 'Action impossible.')
        return redirect('propositions:propositions_demande', pk=demande.pk)
    proposition.statut = Proposition.Statut.ACCEPTEE
    proposition.save()
    Proposition.objects.filter(demande=demande).exclude(pk=proposition.pk).update(
        statut=Proposition.Statut.REFUSEE
    )
    mission = Mission.objects.create(
        demande=demande,
        proposition=proposition,
        client=demande.client,
        prestataire=proposition.prestataire,
    )
    demande.statut = Demande.Statut.MISSION_ACTIVE
    demande.save()
    messages.success(request, 'Proposition acceptée ! Une mission a été créée.')
    return redirect('propositions:detail_mission', pk=mission.pk)


@login_required
def refuser_proposition(request, pk):
    proposition = get_object_or_404(Proposition, pk=pk)
    if proposition.demande.client != request.user:
        messages.error(request, 'Action impossible.')
        return redirect('demandes:mes_demandes')
    proposition.statut = Proposition.Statut.REFUSEE
    proposition.save()
    messages.success(request, 'Proposition refusée.')
    return redirect('propositions:propositions_demande', pk=proposition.demande.pk)


@login_required
def liste_missions(request):
    missions = Mission.objects.filter(
        client=request.user
    ) | Mission.objects.filter(prestataire=request.user)
    missions = missions.distinct().select_related('demande', 'prestataire', 'client')
    return render(request, 'propositions/liste_missions.html', {'missions': missions})


@login_required
def detail_mission(request, pk):
    mission = get_object_or_404(Mission, pk=pk)
    if request.user not in (mission.client, mission.prestataire):
        messages.error(request, 'Tu ne participes pas à cette mission.')
        return redirect('propositions:liste_missions')
    return render(request, 'propositions/detail_mission.html', {'mission': mission})


@login_required
def clore_mission(request, pk):
    mission = get_object_or_404(Mission, pk=pk)
    if request.user not in (mission.client, mission.prestataire):
        messages.error(request, 'Action impossible.')
        return redirect('propositions:liste_missions')
    mission.statut = Mission.Statut.TERMINEE
    mission.save()
    mission.demande.statut = Demande.Statut.CLOTUREE
    mission.demande.save()
    messages.success(request, 'Mission clôturée. Merci !')
    return redirect('propositions:detail_mission', pk=mission.pk)


@login_required
def evaluer_mission(request, pk):
    mission = get_object_or_404(Mission, pk=pk)
    if request.user not in (mission.client, mission.prestataire):
        messages.error(request, 'Action impossible.')
        return redirect('propositions:liste_missions')
    if mission.statut != Mission.Statut.TERMINEE:
        messages.warning(request, 'Évaluation possible une fois la mission terminée.')
        return redirect('propositions:detail_mission', pk=mission.pk)
    cible = mission.prestataire if request.user == mission.client else mission.client
    if request.method == 'POST':
        form = EvaluationForm(request.POST)
        if form.is_valid():
            evaluation = form.save(commit=False)
            evaluation.mission = mission
            evaluation.auteur = request.user
            evaluation.cible = cible
            evaluation.save()
            messages.success(request, 'Merci pour ton évaluation !')
            return redirect('propositions:detail_mission', pk=mission.pk)
    else:
        form = EvaluationForm()
    return render(request, 'propositions/evaluer.html', {'form': form, 'mission': mission, 'cible': cible})


@login_required
def enregistrer_paiement(request, pk):
    mission = get_object_or_404(Mission, pk=pk)
    if request.user != mission.client:
        messages.error(request, 'Seul le client peut enregistrer un paiement.')
        return redirect('propositions:detail_mission', pk=mission.pk)
    if request.method == 'POST':
        form = PaiementForm(request.POST)
        if form.is_valid():
            paiement = form.save(commit=False)
            paiement.mission = mission
            paiement.save()
            messages.success(request, 'Paiement enregistré.')
            return redirect('propositions:detail_mission', pk=mission.pk)
    else:
        initial = {'montant': mission.proposition.prix} if mission.proposition else {}
        form = PaiementForm(initial=initial)
    return render(request, 'propositions/enregistrer_paiement.html', {'form': form, 'mission': mission})