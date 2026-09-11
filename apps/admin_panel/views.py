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
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import Abonnement, Notification, User
from apps.accounts.notifications import creer_notification
from apps.demandes.models import Demande
from apps.paiements.services import confirmer_paiement as confirmer_paiement_service
from apps.propositions.models import Commission, Mission, Paiement


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
        'commissions_en_retard': Commission.objects.filter(
            statut=Commission.Statut.EN_ATTENTE, date_limite__lt=timezone.now()
        ).count(),
        'commissions_a_confirmer': Commission.objects.filter(
            statut=Commission.Statut.EN_ATTENTE, date_declaration__isnull=False
        ).count(),
        'paiements_a_confirmer': Paiement.objects.filter(
            statut=Paiement.Statut.EN_ATTENTE
        ).count(),
        'abonnements_a_confirmer': Abonnement.objects.filter(
            statut=Abonnement.Statut.EN_ATTENTE
        ).count(),
    }
    return render(request, 'admin_panel/dashboard.html', contexte)


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
    """Liste les missions en litige nécessitant l'intervention du back-office."""
    litiges = Mission.objects.filter(statut=Mission.Statut.LITIGE).select_related(
        'demande', 'client', 'prestataire'
    )
    return render(request, 'admin_panel/litiges.html', {'litiges': litiges})


@staff_member_required
def clore_litige(request, pk):
    """Clôture un litige : bascule la mission et sa demande en statut clôturée."""
    mission = Mission.objects.get(pk=pk)
    mission.statut = Mission.Statut.CLOTUREE
    mission.save()
    # La demande associée est clôturée en même temps que la mission.
    mission.demande.statut = Demande.Statut.CLOTUREE
    mission.demande.save()
    messages.success(request, f'Litige clôturé : {mission.demande.titre}')
    return redirect('admin_panel:litiges')


@staff_member_required
def liste_commissions(request):
    """Liste les commissions de la plateforme, les impayées et en retard d'abord."""
    commissions = Commission.objects.select_related(
        'mission__demande', 'mission__prestataire', 'mission__client'
    ).order_by('statut', 'date_limite')
    # Nombre de commission impayées pour le tableau de bord.
    en_attente = Commission.objects.filter(statut=Commission.Statut.EN_ATTENTE).count()
    en_retard = [c for c in commissions if c.en_retard]
    # Commissions dont le prestataire a déjà déclaré le règlement (à confirmer).
    a_confirmer = Commission.objects.filter(
        statut=Commission.Statut.EN_ATTENTE, date_declaration__isnull=False
    ).count()
    return render(request, 'admin_panel/commissions.html', {
        'commissions': commissions,
        'en_attente': en_attente,
        'en_retard': en_retard,
        'a_confirmer': a_confirmer,
    })


@staff_member_required
def confirmer_commission(request, pk):
    """Confirme le règlement d'une commission : le prestataire est réactivé si tout est payé."""
    commission = get_object_or_404(Commission, pk=pk)
    commission.statut = Commission.Statut.PAYEE
    commission.date_paiement = timezone.now()
    commission.save()
    # Si le prestataire n'a plus aucune commission impayée, on lève la sanction.
    prestataire = commission.mission.prestataire
    reste_impaye = Commission.objects.filter(
        mission__prestataire=prestataire, statut=Commission.Statut.EN_ATTENTE
    ).exists()
    if not reste_impaye:
        prestataire.suspendu = False
        prestataire.date_suspension = None
        prestataire.save()
        messages.success(request, f'Commission confirmée — {prestataire.username} est réactivé.')
    else:
        messages.success(request, f'Commission {commission.montant} FCFA confirmée.')
    creer_notification(
        [prestataire],
        f'Ta commission de {commission.montant} FCFA a été confirmée. Merci !',
        Notification.Type.COMMISSION,
        reverse('propositions:mes_commissions'),
    )
    return redirect('admin_panel:commissions')


@staff_member_required
def prolonger_commission(request, pk):
    """Prolonge la date limite de règlement d'une commission impayée."""
    commission = get_object_or_404(Commission, pk=pk)
    commission.date_limite = timezone.now() + timedelta(days=settings.COMMISSION_DELAI_JOURS)
    commission.save()
    messages.success(request, f'Date limite prolongée de {settings.COMMISSION_DELAI_JOURS} jours.')
    return redirect('admin_panel:commissions')


@staff_member_required
def suspendre_prestataire(request, pk):
    """Suspend manuellement un prestataire (accès restreint à la page de règle)."""
    prestataire = get_object_or_404(User, pk=pk, role=User.Role.PRESTATAIRE)
    prestataire.suspendu = True
    prestataire.date_suspension = timezone.now()
    prestataire.save()
    messages.warning(request, f'{prestataire.username} est suspendu.')
    return redirect('admin_panel:prestataires')


@staff_member_required
def bannir_prestataire(request, pk):
    """Bannit définitivement un prestataire (compte désactivé, connexion impossible)."""
    prestataire = get_object_or_404(User, pk=pk, role=User.Role.PRESTATAIRE)
    prestataire.is_active = False
    prestataire.suspendu = False
    prestataire.save()
    messages.error(request, f'{prestataire.username} est banni.')
    return redirect('admin_panel:prestataires')


@staff_member_required
def reactiver_prestataire(request, pk):
    """Rétablit un prestataire suspendu ou banni (sanctions levées)."""
    prestataire = get_object_or_404(User, pk=pk, role=User.Role.PRESTATAIRE)
    prestataire.is_active = True
    prestataire.suspendu = False
    prestataire.date_suspension = None
    prestataire.save()
    messages.success(request, f'{prestataire.username} est réactivé.')
    return redirect('admin_panel:prestataires')


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