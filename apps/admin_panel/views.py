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
from django.utils import timezone

from apps.accounts.models import User
from apps.demandes.models import Demande
from apps.propositions.models import Commission, Mission


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
    }
    return render(request, 'admin_panel/dashboard.html', contexte)


@staff_member_required
def liste_prestataires(request):
    """Liste tous les prestataires inscrits, des plus récents aux plus anciens."""
    prestataires = User.objects.filter(role=User.Role.PRESTATAIRE).order_by('-date_joined')
    return render(request, 'admin_panel/prestataires.html', {'prestataires': prestataires})


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
    messages.success(request, f'Demande validée : {demande.titre}')
    return redirect('admin_panel:demandes')


@staff_member_required
def refuser_demande(request, pk):
    """Supprime une demande jugée non conforme lors de la modération."""
    demande = Demande.objects.get(pk=pk)
    titre = demande.titre
    demande.delete()
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
    return render(request, 'admin_panel/commissions.html', {
        'commissions': commissions,
        'en_attente': en_attente,
        'en_retard': en_retard,
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