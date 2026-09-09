"""
Module de vues pour l'application accounts.

Gere l'ensemble des flux utilisateur : page d'accueil, inscription,
connexion (avec protection brute-force), deconnexion, consultation et
edition du profil.  Chaque vue redirige automatiquement vers l'espace
approprie selon le role de l'utilisateur (client ou prestataire).
"""

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from .forms import ConnexionForm, DemandeAbonnementForm, InscriptionForm, ProfilForm
from .models import Abonnement, User
from .security import enregistrer_echec, reinitialiser_echecs, tentative_autorisee


def accueil(request):
    """Page d'accueil du site.

    - Utilisateur connecte : redirection vers son tableau de bord role.
    - Utilisateur anonyme : affichage de la landing page.
    """
    if request.user.is_authenticated:
        return redirect(accueil_selon_role(request.user))
    return render(request, 'accounts/accueil.html')


def accueil_selon_role(user):
    """Renvoie le nom de la vue d'accueil adapte au role de ``user``.

    - ``None``            -> page de connexion
    - role ``prestataire``-> catalogue public des demandes
    - role ``client``     -> liste de ses propres demandes
    """
    if user is None:
        return 'accounts:connexion'
    if user.role == 'prestataire':
        return 'demandes:catalogue'
    return 'demandes:mes_demandes'


def cgu(request):
    """Page statique « Conditions générales d'utilisation » de la plateforme."""
    return render(request, 'accounts/cgu.html')


def inscription(request):
    """Inscription d'un nouveau compte utilisateur.

    GET  : affiche le formulaire vierge.
    POST : valide et cree l'utilisateur, puis le connecte automatiquement
           et redirige vers son espace.
    """
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
    """Authentification de l'utilisateur avec protection brute-force.

    Avant toute validation du formulaire, verifie que le login n'a pas
    depasse le nombre maximal de tentatives echouees autorisees (cf.
    ``security.tentative_autorisee``).  En cas de succes le compteur
    est reinitialise ; en cas d'echec il est incremente.
    """
    if request.user.is_authenticated:
        return redirect(accueil_selon_role(request.user))
    if request.method == 'POST':
        login_saisi = request.POST.get('username', '')
        # --- Contre-mesure brute-force : blocage si trop d'echecs ---
        if not tentative_autorisee(login_saisi):
            messages.error(request, 'Trop de tentatives échouées. Réessaie dans 15 minutes.')
            form = ConnexionForm()
        else:
            form = ConnexionForm(request, data=request.POST)
            if form.is_valid():
                user = form.get_user()
                login(request, user)
                # Reinitialisation du compteur d'echecs apres succes
                reinitialiser_echecs(login_saisi)
                messages.success(request, f'Content de te revoir {user.username} !')
                return redirect(accueil_selon_role(user))
            # Enregistrement de l'echec dans le cache
            enregistrer_echec(login_saisi)
    else:
        form = ConnexionForm()
    return render(request, 'accounts/connexion.html', {'form': form})


@login_required
def deconnexion(request):
    """Deconnexion de l'utilisateur et redirection vers la page de connexion."""
    logout(request)
    messages.info(request, 'Tu es bien déconnecté.')
    return redirect('accounts:connexion')


@login_required
def profil(request):
    """Affiche la page de profil de l'utilisateur connecte."""
    return render(request, 'accounts/profil.html')


@login_required
def modifier_profil(request):
    """Edition du profil de l'utilisateur connecte.

    GET  : formulaire pre-rempli avec les donnees courantes.
    POST : validation et enregistrement (y compris l'avatar).
    """
    if request.method == 'POST':
        # request.FILES gere le telechargement d'avatar
        form = ProfilForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profil mis à jour.')
            return redirect('accounts:profil')
    else:
        form = ProfilForm(instance=request.user)
    return render(request, 'accounts/modifier_profil.html', {'form': form})


@login_required
def abonnement(request):
    """Page d'abonnement du prestataire : plan en cours, quota et demande d'upgrade.

    Le prestataire choisit un plan payant (Standard/Pro) et un moyen de paiement :
    la demande est créée en « en attente », confirmée ensuite par un admin (back-office).
    """
    if request.user.role != User.Role.PRESTATAIRE:
        messages.error(request, 'Seul un prestataire peut souscrire un abonnement.')
        return redirect('demandes:mes_demandes')
    autorise, utilisees, quota = request.user.peut_proposer()
    en_attente = request.user.abonnements.filter(
        statut=Abonnement.Statut.EN_ATTENTE
    ).first()
    if request.method == 'POST':
        form = DemandeAbonnementForm(request.POST)
        if en_attente:
            messages.warning(request, 'Une demande d’abonnement est déjà en attente de confirmation.')
            return redirect('accounts:abonnement')
        if form.is_valid():
            demande = form.save(commit=False)
            demande.prestataire = request.user
            demande.montant = {
                User.Plan.STANDARD: settings.PLAN_STANDARD_PRIX,
                User.Plan.PRO: settings.PLAN_PRO_PRIX,
            }[demande.plan]
            demande.save()
            messages.info(
                request,
                f'Demande d’abonnement {demande.get_plan_display()} ({demande.montant} FCFA) '
                'enregistrée. Un administrateur va la confirmer.',
            )
            return redirect('accounts:abonnement')
    else:
        form = DemandeAbonnementForm()
    return render(request, 'accounts/abonnement.html', {
        'form': form,
        'autorise': autorise,
        'utilisees': utilisees,
        'quota': quota,
        'en_attente': en_attente,
    })
