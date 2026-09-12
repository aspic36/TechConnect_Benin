"""
Vues de l'app propositions.

Gère le cycle de vie des propositions, missions, évaluations et paiements :
soumission d'une offre par un prestataire, acceptation/refus par le client,
lancement et clôture de mission, évaluation (note 1-5) et paiement accord direct.
"""

from datetime import timedelta

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import Notification
from apps.accounts.notifications import creer_notification, notifier_staff
from apps.demandes.models import Demande
from apps.paiements import services
from apps.paiements.providers.fedapay import ErreurFedaPay, PaiementNonAutorise

from .forms import EvaluationForm, PropositionForm, ReglementCommissionForm
from .models import Commission, Evaluation, Mission, Paiement, Proposition


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
    # Quota mensuel de propositions selon le plan d'abonnement du prestataire.
    autorise, utilisees, quota = request.user.peut_proposer()
    if not autorise:
        messages.error(
            request,
            f'Quota de {quota} propositions/mois atteint. '
            'Passe à un plan supérieur pour continuer à proposer.',
        )
        return redirect('accounts:abonnement')
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
    creer_notification(
        [proposition.prestataire],
        f'Ta proposition pour « {demande.titre} » a été acceptée ! Mission lancée.',
        Notification.Type.MISSION,
        reverse('propositions:detail_mission', args=[mission.pk]),
    )
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
    """Affiche le détail d'une mission, réservé aux deux parties prenantes."""
    mission = get_object_or_404(Mission, pk=pk)
    # Restriction : seuls le client et le prestataire de la mission y accèdent.
    if request.user not in (mission.client, mission.prestataire):
        messages.error(request, 'Tu ne participes pas à cette mission.')
        return redirect('propositions:liste_missions')
    return render(request, 'propositions/detail_mission.html', {
        'mission': mission,
        'reste_a_payer': services.prix_a_payer(mission),
        'mission_payee': services.mission_payee(mission),
    })


@login_required
def clore_mission(request, pk):
    """Clôture une mission : blocage tant que le paiement n'est pas confirmé,
    reversement du solde au prestataire et règlement auto de la commission."""
    mission = get_object_or_404(Mission, pk=pk)
    # Seules les deux parties de la mission peuvent la clôturer.
    if request.user not in (mission.client, mission.prestataire):
        messages.error(request, 'Action impossible.')
        return redirect('propositions:liste_missions')
    # Escrow : la clôture exige que le prix soit intégralement réglé.
    if mission.statut == Mission.Statut.EN_COURS and not services.mission_payee(mission):
        reste = services.prix_a_payer(mission)
        messages.error(
            request,
            f'Le paiement de la mission n’est pas encore confirmé '
            f'(reste {reste} FCFA). Le client doit régler avant la clôture.',
        )
        return redirect('propositions:detail_mission', pk=mission.pk)
    mission.statut = Mission.Statut.TERMINEE
    mission.save()
    # La demande associée est clôturée en même temps que la mission.
    mission.demande.statut = Demande.Statut.CLOTUREE
    mission.demande.save()
    # La clôture déclenche le reversement du solde au prestataire : la
    # commission (COMMISSION_POURCENT %) est réglée automatiquement sur ce
    # reversement. Idempotent : la commission n'est créée qu'une seule fois.
    if not hasattr(mission, 'commission'):
        commission, _ = services.creer_commission_si_absente(mission)
        reversement_ok = services.reverser_prestataire(mission, commission)
        if reversement_ok:
            messages.info(
                request,
                f'Solde de {mission.proposition.prix - commission.montant} FCFA '
                f'reversé au prestataire ; commission plateforme '
                f'({commission.montant} FCFA) réglée automatiquement.',
            )
        else:
            messages.warning(
                request,
                'Le reversement automatique est momentanément indisponible : '
                'une commission de clôture a été créée et sera réglée par l’équipe.',
            )
    messages.success(request, 'Mission clôturée. Merci !')
    return redirect('propositions:detail_mission', pk=mission.pk)


@login_required
def mes_commissions(request):
    """Liste les commissions dues par le prestataire connecté, des plus urgentes aux moins urgentes."""
    if request.user.role != 'prestataire':
        messages.error(request, 'Seul un prestataire a des commissions à régler.')
        return redirect('propositions:liste_missions')
    commissions = Commission.objects.filter(
        mission__prestataire=request.user,
    ).select_related('mission__demande', 'mission__client').order_by('date_limite')
    return render(request, 'propositions/mes_commissions.html', {'commissions': commissions})


@login_required
def regler_commission(request, pk):
    """Permet au prestataire de déclarer le règlement de sa commission."""
    commission = get_object_or_404(Commission, pk=pk, mission__prestataire=request.user)
    # Seul le prestataire concerné peut régler sa propre commission.
    if request.user != commission.mission.prestataire:
        messages.error(request, 'Action impossible.')
        return redirect('propositions:mes_commissions')
    if commission.statut == Commission.Statut.PAYEE:
        messages.info(request, 'Cette commission est déjà réglée.')
        return redirect('propositions:mes_commissions')
    if request.method == 'POST':
        form = ReglementCommissionForm(request.POST, instance=commission)
        if form.is_valid():
            # Enregistre la déclaration : le paiement reste en attente jusqu'à
            # la confirmation de l'administrateur dans le back-office.
            commission = form.save(commit=False)
            commission.date_declaration = timezone.now()
            commission.save()
            notifier_staff(
                f'{request.user.username} a déclaré le règlement de sa commission '
                f'({commission.montant} FCFA).',
                Notification.Type.COMMISSION,
                reverse('admin_panel:commissions'),
            )
            messages.success(
                request,
                'Règlement déclaré. Un administrateur va confirmer ta commission.',
            )
            return redirect('propositions:mes_commissions')
    else:
        form = ReglementCommissionForm()
    return render(request, 'propositions/regler_commission.html', {'form': form, 'commission': commission})


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
def initier_paiement(request, pk):
    """Lance la collecte escrow du prix de la mission (paiement à l'avance).

    Le client choisit son opérateur Mobile Money : la transaction est créée
    chez FedaPay et il est redirigé vers la page de paiement sécurisée.
    Le virement bancaire (repli) reste un enregistrement en attente de
    confirmation par l'équipe.
    """
    mission = get_object_or_404(Mission, pk=pk)
    # Seul le client de la mission peut initier le paiement.
    if request.user != mission.client:
        messages.error(request, 'Seul le client peut payer la mission.')
        return redirect('propositions:detail_mission', pk=mission.pk)
    reste = services.prix_a_payer(mission)
    if reste <= 0:
        messages.info(request, 'Cette mission est déjà intégralement réglée.')
        return redirect('propositions:detail_mission', pk=mission.pk)
    if request.method == 'POST':
        methode = request.POST.get('methode', '')
        if methode not in Paiement.Methode.values:
            messages.error(request, 'Moyen de paiement invalide.')
            return redirect('propositions:detail_mission', pk=mission.pk)
        try:
            paiement, url = services.initier_collecte_mission(
                mission, request.user, methode,
                callback_url=request.build_absolute_uri(reverse('paiements:retour')),
                reference=f'M{mission.pk}-{timezone.now():%Y%m%d%H%M%S}',
            )
        except (ErreurFedaPay, PaiementNonAutorise):
            messages.error(
                request,
                'Le service de paiement est momentanément indisponible. '
                'Réessaie dans quelques instants.',
            )
            return redirect('propositions:detail_mission', pk=mission.pk)
        if url:
            messages.info(request, 'Tu es redirigé vers le paiement sécurisé FedaPay.')
            return redirect(url)
        messages.info(
            request,
            'Ton paiement est enregistré : il sera confirmé par l’équipe '
            'avant la clôture de la mission.',
        )
        return redirect('propositions:detail_mission', pk=mission.pk)
    return render(request, 'propositions/payer_mission.html', {
        'mission': mission,
        'reste': reste,
        'methodes': Paiement.Methode,
        'fedapay_sandbox': settings.FEDAPAY_MODE == 'sandbox',
    })


@login_required
def verifier_paiement(request, pk):
    """Interroge FedaPay et confirme les paiements passés en ``approved``."""
    mission = get_object_or_404(Mission, pk=pk)
    if request.user != mission.client:
        messages.error(request, 'Seul le client peut vérifier le paiement.')
        return redirect('propositions:detail_mission', pk=mission.pk)
    if services.mission_payee(mission):
        messages.info(request, 'Cette mission est déjà intégralement réglée.')
        return redirect('propositions:detail_mission', pk=mission.pk)
    en_cours = mission.paiements.filter(
        statut=Paiement.Statut.EN_COURS,
    ).exclude(reference_txn='').exclude(reference_txn__isnull=True)
    if not en_cours:
        messages.warning(request, 'Aucun paiement en cours à vérifier.')
        return redirect('propositions:detail_mission', pk=mission.pk)
    confirme = 0
    for paiement in en_cours:
        try:
            statut_fedapay = services.get_provider().verifier_transaction(paiement.reference_txn)
        except ErreurFedaPay:
            continue
        if statut_fedapay == 'approved':
            services.confirmer_paiement(paiement)
            confirme += 1
        elif statut_fedapay in ('failed', 'cancelled'):
            services.eclater_paiement(paiement)
    if confirme:
        messages.success(request, f'{confirme} paiement(s) confirmé(s). Le prestataire est prévenu.')
    else:
        messages.info(request, 'Les paiements sont toujours en attente de confirmation.')
    return redirect('propositions:detail_mission', pk=mission.pk)