"""
Vues de l'app propositions.

Gère le cycle de vie des propositions, missions, évaluations et paiements :
soumission d'une offre par un prestataire, acceptation/refus par le client,
lancement et clôture de mission, évaluation (note 1-5) et paiement accord direct.
"""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from apps.demandes.models import Demande

from .forms import EvaluationForm, PaiementForm, PropositionForm
from .models import Evaluation, Mission, Paiement, Proposition


@login_required
def soumettre_proposition(request, pk):
    """Permet à un prestataire de soumettre une offre pour une demande donnée."""
    demande = get_object_or_404(Demande, pk=pk)
    # Seul un prestataire peut soumettre une proposition.
    if request.user.role != 'prestataire':
        messages.error(request, 'Seul un prestataire peut soumettre une proposition.')
        return redirect('demandes:catalogue')
    # Une demande déjà lancée ou clôturée ne reçoit plus de propositions.
    if demande.statut not in (Demande.Statut.EN_COURS, Demande.Statut.EN_ATTENTE):
        messages.warning(request, 'Cette demande ne reçoit plus de propositions.')
        return redirect('demandes:detail_demande', pk=demande.pk)
    if request.method == 'POST':
        form = PropositionForm(request.POST)
        if form.is_valid():
            proposition = form.save(commit=False)
            # On rattache la proposition à la demande et au prestataire connecté.
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
    """Affiche la liste des propositions soumises par le prestataire connecté."""
    propositions = Proposition.objects.filter(prestataire=request.user).select_related('demande')
    return render(request, 'propositions/mes_propositions.html', {'propositions': propositions})


@login_required
def propositions_demande(request, pk):
    """Affiche les propositions reçues pour une demande, uniquement pour son client."""
    # Le client ne voit que les propositions de ses propres demandes (confidentialité).
    demande = get_object_or_404(Demande, pk=pk, client=request.user)
    propositions = demande.propositions.all().select_related('prestataire')
    return render(request, 'propositions/propositions_demande.html', {
        'demande': demande,
        'propositions': propositions,
    })


@login_required
def accepter_proposition(request, pk):
    """
    Accepte une proposition : crée la mission et refuse automatiquement les autres.

    Seul le client de la demande peut agir, et une seule fois (une mission existe déjà).
    """
    proposition = get_object_or_404(Proposition, pk=pk)
    demande = proposition.demande
    has_mission = hasattr(demande, 'mission')
    # Vérifie le droit du client et qu'aucune mission n'a déjà été créée.
    if demande.client != request.user or has_mission:
        messages.error(request, 'Action impossible.')
        return redirect('propositions:propositions_demande', pk=demande.pk)
    # La proposition choisie passe en "acceptée", les autres en "refusée".
    proposition.statut = Proposition.Statut.ACCEPTEE
    proposition.save()
    Proposition.objects.filter(demande=demande).exclude(pk=proposition.pk).update(
        statut=Proposition.Statut.REFUSEE
    )
    # Création de la mission liée à la demande et à la proposition acceptée.
    mission = Mission.objects.create(
        demande=demande,
        proposition=proposition,
        client=demande.client,
        prestataire=proposition.prestataire,
    )
    # La demande passe en statut "mission active".
    demande.statut = Demande.Statut.MISSION_ACTIVE
    demande.save()
    messages.success(request, 'Proposition acceptée ! Une mission a été créée.')
    return redirect('propositions:detail_mission', pk=mission.pk)


@login_required
def refuser_proposition(request, pk):
    """Refuse une proposition sans lancer de mission (action du client)."""
    proposition = get_object_or_404(Proposition, pk=pk)
    # Seul le client propriétaire de la demande peut refuser une proposition.
    if proposition.demande.client != request.user:
        messages.error(request, 'Action impossible.')
        return redirect('demandes:mes_demandes')
    proposition.statut = Proposition.Statut.REFUSEE
    proposition.save()
    messages.success(request, 'Proposition refusée.')
    return redirect('propositions:propositions_demande', pk=proposition.demande.pk)


@login_required
def liste_missions(request):
    """Liste les missions auxquelles participe l'utilisateur connecté (client ou prestataire)."""
    # Réunion des missions où l'utilisateur est client ou prestataire.
    missions = Mission.objects.filter(
        client=request.user
    ) | Mission.objects.filter(prestataire=request.user)
    missions = missions.distinct().select_related('demande', 'prestataire', 'client')
    return render(request, 'propositions/liste_missions.html', {'missions': missions})


@login_required
def detail_mission(request, pk):
    """Affiche le détail d'une mission, réservé aux deux parties concernées."""
    mission = get_object_or_404(Mission, pk=pk)
    # Restriction : seuls le client et le prestataire de la mission y accèdent.
    if request.user not in (mission.client, mission.prestataire):
        messages.error(request, 'Tu ne participes pas à cette mission.')
        return redirect('propositions:liste_missions')
    return render(request, 'propositions/detail_mission.html', {'mission': mission})


@login_required
def clore_mission(request, pk):
    """Clôture une mission : passe la mission et sa demande en statut terminal."""
    mission = get_object_or_404(Mission, pk=pk)
    # Seules les deux parties de la mission peuvent la clôturer.
    if request.user not in (mission.client, mission.prestataire):
        messages.error(request, 'Action impossible.')
        return redirect('propositions:liste_missions')
    mission.statut = Mission.Statut.TERMINEE
    mission.save()
    # La demande associée est clôturée en même temps que la mission.
    mission.demande.statut = Demande.Statut.CLOTUREE
    mission.demande.save()
    messages.success(request, 'Mission clôturée. Merci !')
    return redirect('propositions:detail_mission', pk=mission.pk)


@login_required
def evaluer_mission(request, pk):
    """Permet à une partie de la mission d'évaluer l'autre (note de 1 à 5)."""
    mission = get_object_or_404(Mission, pk=pk)
    # Seuls les participants de la mission peuvent évaluer.
    if request.user not in (mission.client, mission.prestataire):
        messages.error(request, 'Action impossible.')
        return redirect('propositions:liste_missions')
    # L'évaluation n'est possible qu'une fois la mission terminée.
    if mission.statut != Mission.Statut.TERMINEE:
        messages.warning(request, 'Évaluation possible une fois la mission terminée.')
        return redirect('propositions:detail_mission', pk=mission.pk)
    # La cible est le prestataire si l'auteur est le client, et inversement.
    cible = mission.prestataire if request.user == mission.client else mission.client
    if request.method == 'POST':
        form = EvaluationForm(request.POST)
        if form.is_valid():
            evaluation = form.save(commit=False)
            # Rattache l'évaluation à la mission, à l'auteur et à la cible.
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
    """Enregistre un paiement sur une mission (accord direct, seul le client)."""
    mission = get_object_or_404(Mission, pk=pk)
    # Seul le client de la mission peut enregistrer un paiement (accord direct MVP).
    if request.user != mission.client:
        messages.error(request, 'Seul le client peut enregistrer un paiement.')
        return redirect('propositions:detail_mission', pk=mission.pk)
    if request.method == 'POST':
        form = PaiementForm(request.POST)
        if form.is_valid():
            paiement = form.save(commit=False)
            # Rattache le paiement à la mission courante.
            paiement.mission = mission
            paiement.save()
            messages.success(request, 'Paiement enregistré.')
            return redirect('propositions:detail_mission', pk=mission.pk)
    else:
        # Pré-remplit le montant avec le prix de la proposition acceptée si disponible.
        initial = {'montant': mission.proposition.prix} if mission.proposition else {}
        form = PaiementForm(initial=initial)
    return render(request, 'propositions/enregistrer_paiement.html', {'form': form, 'mission': mission})