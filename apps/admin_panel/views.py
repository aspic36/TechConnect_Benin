"""
Vues du back-office (admin_panel).

Réserve aux membres du staff : tableau de bord avec statistiques, vérification des
prestataires, modération des demandes (en_attente → en_cours ou suppression)
et clôture des litiges.
"""

from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import redirect, render

from apps.accounts.models import User
from apps.demandes.models import Demande
from apps.propositions.models import Mission


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