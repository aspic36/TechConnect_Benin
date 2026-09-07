from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from .forms import ConnexionForm, InscriptionForm, ProfilForm
from .security import enregistrer_echec, reinitialiser_echecs, tentative_autorisee


def accueil(request):
    if request.user.is_authenticated:
        return redirect(accueil_selon_role(request.user))
    return render(request, 'accounts/accueil.html')


def accueil_selon_role(user):
    if user is None:
        return 'accounts:connexion'
    if user.role == 'prestataire':
        return 'demandes:catalogue'
    return 'demandes:mes_demandes'


def inscription(request):
    if request.user.is_authenticated:
        return redirect(accueil_selon_role(request.user))
    if request.method == 'POST':
        form = InscriptionForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f'Bienvenue {user.username} !')
            return redirect(accueil_selon_role(user))
    else:
        form = InscriptionForm()
    return render(request, 'accounts/inscription.html', {'form': form})


def connexion(request):
    if request.user.is_authenticated:
        return redirect(accueil_selon_role(request.user))
    if request.method == 'POST':
        login_saisi = request.POST.get('username', '')
        if not tentative_autorisee(login_saisi):
            messages.error(request, 'Trop de tentatives échouées. Réessaie dans 15 minutes.')
            form = ConnexionForm()
        else:
            form = ConnexionForm(request, data=request.POST)
            if form.is_valid():
                user = form.get_user()
                login(request, user)
                reinitialiser_echecs(login_saisi)
                messages.success(request, f'Content de te revoir {user.username} !')
                return redirect(accueil_selon_role(user))
            enregistrer_echec(login_saisi)
    else:
        form = ConnexionForm()
    return render(request, 'accounts/connexion.html', {'form': form})


@login_required
def deconnexion(request):
    logout(request)
    messages.info(request, 'Tu es bien déconnecté.')
    return redirect('accounts:connexion')


@login_required
def profil(request):
    return render(request, 'accounts/profil.html')


@login_required
def modifier_profil(request):
    if request.method == 'POST':
        form = ProfilForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profil mis à jour.')
            return redirect('accounts:profil')
    else:
        form = ProfilForm(instance=request.user)
    return render(request, 'accounts/modifier_profil.html', {'form': form})