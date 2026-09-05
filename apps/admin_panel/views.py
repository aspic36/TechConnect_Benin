from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import redirect, render

from apps.accounts.models import User
from apps.demandes.models import Demande
from apps.propositions.models import Mission


@staff_member_required
def dashboard(request):
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
    prestataires = User.objects.filter(role=User.Role.PRESTATAIRE).order_by('-date_joined')
    return render(request, 'admin_panel/prestataires.html', {'prestataires': prestataires})


@staff_member_required
def verifier_prestataire(request, pk):
    prestataire = User.objects.get(pk=pk)
    prestataire.is_verified = True
    prestataire.save()
    messages.success(request, f'{prestataire.username} est maintenant vérifié.')
    return redirect('admin_panel:prestataires')