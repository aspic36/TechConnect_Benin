from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from apps.propositions.models import Mission

from .models import Message


@login_required
def fil_mission(request, pk):
    mission = get_object_or_404(Mission, pk=pk)
    if request.user not in (mission.client, mission.prestataire):
        messages.error(request, 'Tu ne participes pas à cette mission.')
        return redirect('propositions:liste_missions')
    if request.method == 'POST':
        contenu = request.POST.get('contenu', '').strip()
        if contenu:
            Message.objects.create(mission=mission, expediteur=request.user, contenu=contenu)
        return redirect('messagerie:fil', pk=mission.pk)
    fil = mission.messages.all()
    fil.filter(lu=False).exclude(expediteur=request.user).update(lu=True)
    return render(request, 'messagerie/fil.html', {'mission': mission, 'fil': fil})