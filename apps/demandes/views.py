"""Vues de l'app demandes : création, consultation et catalogue de demandes."""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from apps.accounts.models import Notification
from apps.accounts.notifications import notifier_staff

from .forms import DemandeForm
from .models import Categorie, Demande


@login_required
def creation_demande(request):
    """Permet à un client de créer et publier une nouvelle demande d'aide."""
    # Seul un client peut créer une demande (bloquer les prestataires)
    if request.user.role != 'client':
        messages.error(request, 'Seul un client peut publier une demande.')
        return redirect('demandes:catalogue')
    if request.method == 'POST':
        form = DemandeForm(request.POST)
        if form.is_valid():
            # Associer la demande au client connecté avant sauvegarde
            demande = form.save(commit=False)
            demande.client = request.user
            demande.save()
            notifier_staff(
                f'Nouvelle demande à modérer : « {demande.titre} »',
                Notification.Type.DEMANDE,
                reverse('admin_panel:demandes'),
            )
            messages.success(request, 'Ta demande a été publiée en attente de validation.')
            return redirect('demandes:mes_demandes')
    else:
        form = DemandeForm()
    return render(request, 'demandes/creation_demande.html', {'form': form})


@login_required
def mes_demandes(request):
    """Affiche la liste des demandes appartenant au client connecté."""
    demandes = Demande.objects.filter(client=request.user)
    return render(request, 'demandes/mes_demandes.html', {'demandes': demandes})


@login_required
def catalogue(request):
    """Catalogue public des demandes validées (statut en_cours), consultable par les prestataires."""
    # Seules les demandes validées (en_cours) sont visibles dans le catalogue
    demandes = Demande.objects.filter(statut=Demande.Statut.EN_COURS)
    categorie_slug = request.GET.get('categorie')
    q = request.GET.get('q')
    # Filtrage optionnel par catégorie (slug dans l'URL)
    if categorie_slug:
        demandes = demandes.filter(categorie__slug=categorie_slug)
    # Recherche par mot-clé dans le titre ou la description
    if q:
        demandes = demandes.filter(Q(titre__icontains=q) | Q(description__icontains=q))
    categories = Categorie.objects.all()
    # Infos du quota d'abonnement pour le bandeau d'information du catalogue.
    if request.user.role == 'prestataire':
        autorise, utilisees, quota = request.user.peut_proposer()
        return render(request, 'demandes/catalogue.html', {
            'demandes': demandes,
            'categories': categories,
            'categorie_active': categorie_slug,
            'autorise': autorise,
            'utilisees': utilisees,
            'quota': quota,
            'prochaine_recharge': request.user.prochaine_recharge(),
        })
    return render(request, 'demandes/catalogue.html', {
        'demandes': demandes,
        'categories': categories,
        'categorie_active': categorie_slug,
    })


@login_required
def detail_demande(request, pk):
    """Affiche le détail d'une demande avec contrôle d'accès."""
    demande = get_object_or_404(Demande, pk=pk)
    est_proprietaire = demande.client == request.user
    # Confidentialité : seuls le propriétaire et un prestataire (si la demande est en_cours) peuvent voir la demande
    est_prestataire_public = (
        request.user.role == 'prestataire' and demande.statut == Demande.Statut.EN_COURS
    )
    if not (est_proprietaire or est_prestataire_public):
        messages.error(request, 'Cette demande n\'est pas publique.')
        return redirect('demandes:mes_demandes')
    return render(request, 'demandes/detail_demande.html', {'demande': demande})