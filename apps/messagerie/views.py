"""Vues de la messagerie : fil de messages par mission, envoi et marquage lu."""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from apps.propositions.models import Mission

from .models import Message


@login_required
def fil_mission(request, pk):
    """Affiche et permet d'envoyer des messages dans le fil d'une mission donnée."""
    mission = get_object_or_404(Mission, pk=pk)
    # Sécurité : seuls le client et le prestataire de la mission accèdent au fil
    if request.user not in (mission.client, mission.prestataire):
        messages.error(request, 'Tu ne participes pas à cette mission.')
        return redirect('propositions:liste_missions')
    # Envoi d'un message via POST
    if request.method == 'POST':
        contenu = request.POST.get('contenu', '').strip()
        if contenu:
            Message.objects.create(mission=mission, expediteur=request.user, contenu=contenu)
        return redirect('messagerie:fil', pk=mission.pk)
    fil = mission.messages.all()
    # Marquer comme lus les messages reçus par l'utilisateur connecté
    fil.filter(lu=False).exclude(expediteur=request.user).update(lu=True)
    return render(request, 'messagerie/fil.html', {'mission': mission, 'fil': fil})