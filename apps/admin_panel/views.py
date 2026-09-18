"""
Vues du back-office (admin_panel).

Réserve aux membres du staff : tableau de bord avec statistiques, vérification des
prestataires, modération des demandes (en_attente → en_cours ou suppression)
et clôture des litiges.
"""

from datetime import timedelta

from django.conf import settings
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Avg, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import Abonnement, Notification, User
from apps.accounts.notifications import creer_notification
from apps.demandes.models import Categorie, Demande
from apps.paiements.services import confirmer_paiement as confirmer_paiement_service
from apps.propositions.models import Commission, Litige, Mission, Paiement


@staff_member_required
def dashboard(request):
    """Affiche le tableau de bord avec les indicateurs clés de la plateforme."""
    # Agrégation des compteurs utiles à la supervision de la plateforme.
    contexte = {
        'total_clients': User.objects.filter(role=User.Role.CLIENT).count(),
        'total_prestataires': User.objects.filter(role=User.Role.PRESTATAIRE).count(),
        'prestataires_a_verifier': User.objects.filter(
            role=User.Role.PRESTATAIRE, is_verified=False
        ).count(),
        'total_demandes': Demande.objects.count(),
        'demandes_en_attente': Demande.objects.filter(statut=Demande.Statut.EN_ATTENTE).count(),
        'demandes_en_cours': Demande.objects.filter(statut=Demande.Statut.EN_COURS).count(),
        'missions_en_cours': Mission.objects.filter(statut=Mission.Statut.EN_COURS).count(),
        'missions_terminees': Mission.objects.filter(statut=Mission.Statut.TERMINEE).count(),
        'missions_litiges': Mission.objects.filter(statut=Mission.Statut.LITIGE).count(),
        'commissions_en_attente': Commission.objects.filter(
            statut=Commission.Statut.EN_ATTENTE
        ).count(),
        'revenus_encaisses': Commission.objects.filter(
            statut=Commission.Statut.PAYEE
        ).aggregate(somme=Sum('montant'))['somme'] or 0,
        'paiements_a_confirmer': Paiement.objects.filter(
            statut=Paiement.Statut.EN_ATTENTE
        ).count(),
        'abonnements_a_confirmer': Abonnement.objects.filter(
            statut=Abonnement.Statut.EN_ATTENTE
        ).count(),
    }
    return render(request, 'admin_panel/dashboard.html', contexte)


@staff_member_required
def statistiques(request):
    """Page de statistiques avancées : revenus, missions par catégorie, top prestataires."""
    from django.db.models import Count, Q

    # --- Revenus plateforme (commissions retenues sur les missions clôturées) ---
    commissions_payees = Commission.objects.filter(statut=Commission.Statut.PAYEE)
    commissions_attente = Commission.objects.filter(statut=Commission.Statut.EN_ATTENTE)
    revenus_encaisses = commissions_payees.aggregate(somme=Sum('montant'))['somme'] or 0
    revenus_attente = commissions_attente.aggregate(somme=Sum('montant'))['somme'] or 0
    nb_commissions_payees = commissions_payees.count()

    # --- Volume d'activité global ---
    missions_terminees = Mission.objects.filter(
        statut__in=[Mission.Statut.TERMINEE, Mission.Statut.CLOTUREE]
    )
    ca_total = sum(
        m.proposition.prix for m in missions_terminees.select_related('proposition')
        if m.proposition
    )
    panier_moyen = round(ca_total / missions_terminees.count()) if missions_terminees.exists() else 0

    # --- Missions par catégorie (toutes + clôturées) ---
    categories = Categorie.objects.annotate(
        nb_missions=Count('demandes__mission'),
        nb_terminees=Count(
            'demandes__mission',
            filter=Q(demandes__mission__statut__in=[
                Mission.Statut.TERMINEE, Mission.Statut.CLOTUREE]),
        ),
    ).order_by('-nb_missions')
    max_missions = max((c.nb_missions for c in categories), default=0)

    # --- Top prestataires (missions, note moyenne, chiffre d'affaires) ---
    top_prestataires = []
    for prestataire in User.objects.filter(role=User.Role.PRESTATAIRE).prefetch_related(
            'missions_prestataire', 'evaluations_recues'):
        missions = [m for m in prestataire.missions_prestataire.all()
                    if m.statut in (Mission.Statut.TERMINEE, Mission.Statut.CLOTUREE)]
        if not missions:
            continue
        ca = sum(m.proposition.prix for m in missions if m.proposition)
        notes = [e.note for e in prestataire.evaluations_recues.all()]
        top_prestataires.append({
            'prestataire': prestataire,
            'nb_missions': len(missions),
            'ca': ca,
            'note_moyenne': round(sum(notes) / len(notes), 1) if notes else None,
        })
    top_prestataires.sort(key=lambda x: (x['nb_missions'], x['ca']), reverse=True)
    top_prestataires = top_prestataires[:5]

    return render(request, 'admin_panel/statistiques.html', {
        'revenus_encaisses': revenus_encaisses,
        'revenus_attente': revenus_attente,
        'nb_commissions_payees': nb_commissions_payees,
        'nb_missions_terminees': missions_terminees.count(),
        'missions_en_cours': Mission.objects.filter(statut=Mission.Statut.EN_COURS).count(),
        'missions_litiges': Mission.objects.filter(statut=Mission.Statut.LITIGE).count(),
        'ca_total': ca_total,
        'panier_moyen': panier_moyen,
        'categories': categories,
        'max_missions': max_missions,
        'top_prestataires': top_prestataires,
    })


@staff_member_required
def liste_prestataires(request):
    """Liste tous les prestataires inscrits, des plus récents aux plus anciens."""
    prestataires = User.objects.filter(role=User.Role.PRESTATAIRE).order_by('-date_joined')
    return render(request, 'admin_panel/prestataires.html', {
        'prestataires': prestataires,
        'now': timezone.now(),
    })


@staff_member_required
def verifier_prestataire(request, pk):
    """Marque un prestataire comme vérifié par l'équipe administrative."""
    prestataire = User.objects.get(pk=pk)
    prestataire.is_verified = True
    prestataire.save()
    messages.success(request, f'{prestataire.username} est maintenant vérifié.')
    return redirect('admin_panel:prestataires')


@staff_member_required
def liste_demandes(request):
    """Liste les demandes en attente de validation (modération)."""
    demandes = Demande.objects.filter(statut=Demande.Statut.EN_ATTENTE).select_related('client', 'categorie')
    return render(request, 'admin_panel/demandes.html', {'demandes': demandes})


@staff_member_required
def valider_demande(request, pk):
    """Approuve une demande en attente : elle passe au statut en_cours (publique)."""
    demande = Demande.objects.get(pk=pk)
    demande.statut = Demande.Statut.EN_COURS
    demande.save()
    creer_notification(
        [demande.client],
        f'Ta demande « {demande.titre} » a été validée et est publique !',
        Notification.Type.DEMANDE,
        reverse('demandes:detail_demande', args=[demande.pk]),
    )
    messages.success(request, f'Demande validée : {demande.titre}')
    return redirect('admin_panel:demandes')


@staff_member_required
def refuser_demande(request, pk):
    """Supprime une demande jugée non conforme lors de la modération."""
    demande = Demande.objects.get(pk=pk)
    client = demande.client
    titre = demande.titre
    demande.delete()
    creer_notification(
        [client],
        f'Ta demande « {titre} » a été supprimée par la modération.',
        Notification.Type.DEMANDE,
        reverse('demandes:mes_demandes'),
    )
    messages.success(request, f'Demande supprimée : {titre}')
    return redirect('admin_panel:demandes')


@staff_member_required
def liste_litiges(request):
    """Liste les missions en litige avec le motif et la pièce jointe signalés."""
    missions = Mission.objects.filter(statut=Mission.Statut.LITIGE).select_related(
        'demande', 'client', 'prestataire', 'litige', 'litige__signaleur'
    ).order_by('-litige__date_creation')
    # Chaque fonds reste bloqué : l'équipe décide in fine du reversement.
    return render(request, 'admin_panel/litiges.html', {'litiges': missions})


@staff_member_required
def passer_mediation(request, pk):
    """Ouvre une médiation : invite les deux parties à échanger dans la messagerie."""
    litige = get_object_or_404(Litige, pk=pk)
    if litige.statut == Litige.Statut.CLOS:
        messages.info(request, 'Ce litige est déjà clos.')
        return redirect('admin_panel:litiges')
    litige.statut = Litige.Statut.MEDIATION
    litige.save(update_fields=['statut'])
    creer_notification(
        [litige.mission.client, litige.mission.prestataire],
        f'Médiation ouverte sur « {litige.mission.demande.titre} ». '
        'Échangez avec l’autre partie dans la messagerie pour trouver un accord.',
        Notification.Type.LITIGE,
        reverse('propositions:detail_mission', args=[litige.mission.pk]),
    )
    messages.success(request, f'Médiation engagée — {litige.mission.demande.titre}.')
    return redirect('admin_panel:litiges')


@staff_member_required
def resoudre_litige(request, pk):
    """Résout un litige : clôture la mission et sa demande, notifie la décision."""
    litige = get_object_or_404(Litige, pk=pk)
    if litige.statut == Litige.Statut.CLOS:
        messages.info(request, 'Ce litige est déjà clos.')
        return redirect('admin_panel:litiges')
    decision = request.POST.get('decision', '').strip()
    en_faveur = request.POST.get('en_faveur', '')
    if en_faveur not in Litige.EnFaveur.values:
        en_faveur = ''
    litige.decision = decision
    litige.en_faveur = en_faveur
    litige.statut = Litige.Statut.CLOS
    litige.date_decision = timezone.now()
    litige.save()
    # La mission et sa demande sont clôturées définitivement.
    mission = litige.mission
    mission.statut = Mission.Statut.CLOTUREE
    mission.save(update_fields=['statut'])
    mission.demande.statut = Demande.Statut.CLOTUREE
    mission.demande.save(update_fields=['statut'])
    message = (
        f'Le litige sur « {mission.demande.titre} » est résolu. '
        f'Décision : {litige.get_en_faveur_display() or "avis de l’équipe"}. '
        f'{decision or "Merci de votre confiance."}'
    )
    creer_notification(
        [mission.client, mission.prestataire],
        message,
        Notification.Type.LITIGE,
        reverse('propositions:detail_mission', args=[mission.pk]),
    )
    messages.success(request, f'Litige résolu : {mission.demande.titre}.')
    return redirect('admin_panel:litiges')


@staff_member_required
def liste_commissions(request):
    """Liste les commissions de la plateforme, les en attente d'abord."""
    commissions = Commission.objects.select_related(
        'mission__demande', 'mission__prestataire', 'mission__client'
    ).order_by('statut', 'date_limite')
    en_attente = Commission.objects.filter(statut=Commission.Statut.EN_ATTENTE).count()
    return render(request, 'admin_panel/commissions.html', {
        'commissions': commissions,
        'en_attente': en_attente,
    })


@staff_member_required
def confirmer_commission(request, pk):
    """Marque une commission comme réglée (reversement manuel de blocage)."""
    commission = get_object_or_404(Commission, pk=pk)
    commission.statut = Commission.Statut.PAYEE
    commission.date_paiement = timezone.now()
    commission.save()
    prestataire = commission.mission.prestataire
    creer_notification(
        [prestataire],
        f'Ta commission de {commission.montant} FCFA a été confirmée. Merci !',
        Notification.Type.COMMISSION,
        reverse('propositions:detail_mission', args=[commission.mission.pk]),
    )
    messages.success(request, f'Commission {commission.montant} FCFA confirmée.')
    return redirect('admin_panel:commissions')


@staff_member_required
def liste_paiements(request):
    """Liste les paiements des missions, les en attente de confirmation d'abord."""
    paiements = Paiement.objects.select_related(
        'mission__demande', 'mission__client', 'mission__prestataire'
    ).order_by('statut', '-date_creation')
    a_confirmer = Paiement.objects.filter(statut=Paiement.Statut.EN_ATTENTE).count()
    return render(request, 'admin_panel/paiements.html', {
        'paiements': paiements,
        'a_confirmer': a_confirmer,
    })


@staff_member_required
def confirmer_paiement(request, pk):
    """Confirme un paiement en attente (virement bancaire ou repli local)."""
    paiement = get_object_or_404(Paiement, pk=pk)
    if paiement.statut == Paiement.Statut.EN_ATTENTE:
        confirmer_paiement_service(paiement)
        messages.success(
            request,
            f'Paiement de {paiement.montant} FCFA confirmé pour '
            f'« {paiement.mission.demande.titre} ».',
        )
    else:
        messages.info(request, 'Ce paiement a déjà été traité.')
    return redirect('admin_panel:paiements')


@staff_member_required
def liste_abonnements(request):
    """Liste les demandes d'abonnement des prestataires, les en attente d'abord."""
    abonnements = Abonnement.objects.select_related('prestataire').order_by('statut', '-date_demande')
    a_attente = Abonnement.objects.filter(statut=Abonnement.Statut.EN_ATTENTE).count()
    return render(request, 'admin_panel/abonnements.html', {
        'abonnements': abonnements,
        'en_attente': a_attente,
    })


@staff_member_required
def confirmer_abonnement(request, pk):
    """Confirme une demande d'abonnement et active la période sur le compte."""
    abonnement = get_object_or_404(Abonnement, pk=pk)
    if abonnement.statut == Abonnement.Statut.EN_ATTENTE:
        maintenant = timezone.now()
        abonnement.statut = Abonnement.Statut.ACTIF
        abonnement.date_confirmation = maintenant
        abonnement.date_fin = maintenant + timedelta(days=settings.ABONNEMENT_DUREE_JOURS)
        abonnement.save()
        # Active le plan sur le compte du prestataire pour la durée payée.
        prestataire = abonnement.prestataire
        prestataire.plan = abonnement.plan
        prestataire.date_debut_plan = maintenant
        prestataire.date_fin_plan = abonnement.date_fin
        prestataire.save()
        creer_notification(
            [prestataire],
            f'Ton abonnement {abonnement.get_plan_display()} est confirmé ! '
            f'Actif 30 jours jusqu’au {abonnement.date_fin:%d/%m/%Y}.',
            Notification.Type.ABONNEMENT,
            reverse('accounts:abonnement'),
        )
        messages.success(
            request,
            f'Abonnement {abonnement.get_plan_display()} activé pour '
            f'{prestataire.username} ({abonnement.montant} FCFA).',
        )
    else:
        messages.info(request, 'Cette demande a déjà été traitée.')
    return redirect('admin_panel:abonnements')


@staff_member_required
def refuser_abonnement(request, pk):
    """Refuse une demande d'abonnement (le compte reste sur le plan courant)."""
    abonnement = get_object_or_404(Abonnement, pk=pk)
    if abonnement.statut == Abonnement.Statut.EN_ATTENTE:
        abonnement.statut = Abonnement.Statut.REFUSE
        abonnement.save()
        creer_notification(
            [abonnement.prestataire],
            f'Ton abonnement {abonnement.get_plan_display()} a été refusé. '
            'Reprends contact avec l’administration.',
            Notification.Type.ABONNEMENT,
            reverse('accounts:abonnement'),
        )
        messages.warning(request, f'Demande {abonnement.get_plan_display()} refusée.')
    return redirect('admin_panel:abonnements')