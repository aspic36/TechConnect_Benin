"""Vues de l'app demandes : création, consultation et catalogue de demandes."""

from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from apps.accounts.models import Notification, User
from apps.accounts.notifications import notifier_staff

from .forms import DemandeForm
from .models import Categorie, Demande, FavorisDemande


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
    """Catalogue public des demandes validées, avec filtres et pagination.

    Filtres cumulables (via la query string ``GET``) :
      - ``q``          : recherche plein-texte sur le titre / la description
      - ``categorie``  : slug d'une catégorie
      - ``budget_min`` / ``budget_max`` : fourchette de budget (FCFA), testée
        en recouvrement avec l'intervalle annoncé par le client
      - ``ville``      : ville du prestataire attendue (``lieu``)
      - ``a_distance`` : ne garder que les demandes acceptant le télétravail
    Les résultats sont paginés (12 demandes par page).
    """
    demandes = Demande.objects.filter(
        statut=Demande.Statut.EN_COURS
    ).select_related('categorie')

    # --- Collecte des filtres depuis la query string ---
    q = request.GET.get('q', '').strip()
    categorie_slug = request.GET.get('categorie', '')
    budget_min = request.GET.get('budget_min', '').strip()
    budget_max = request.GET.get('budget_max', '').strip()
    ville = request.GET.get('ville', '').strip()
    a_distance = request.GET.get('a_distance', '') == '1'

    # --- Application des filtres ---
    if q:
        demandes = demandes.filter(Q(titre__icontains=q) | Q(description__icontains=q))
    if categorie_slug:
        demandes = demandes.filter(categorie__slug=categorie_slug)
    if ville:
        demandes = demandes.filter(lieu__icontains=ville)
    if a_distance:
        demandes = demandes.filter(a_distance=True)
    # Budget : la demande doit accepter au moins une partie de la fourchette demandée.
    try:
        if budget_min:
            demandes = demandes.filter(budget_max__gte=Decimal(budget_min))
        if budget_max:
            demandes = demandes.filter(budget_min__lte=Decimal(budget_max))
    except InvalidOperation:
        budget_min = budget_max = ''  # montants invalides → filtre ignoré

    # --- Pagination (12 demandes par page) ---
    demandes = demandes.order_by('-date_creation')
    paginator = Paginator(demandes, 12)
    page_obj = paginator.get_page(request.GET.get('page'))

    categories = Categorie.objects.annotate(
        nb=Count('demandes', filter=Q(demandes__statut=Demande.Statut.EN_COURS))
    ).order_by('nom')

    # --- Favoris du prestataire (pour marquer les demandes « en favori ») ---
    favoris_ids = set()
    if request.user.role == User.Role.PRESTATAIRE:
        favoris_ids = set(FavorisDemande.objects.filter(
            prestataire=request.user)
            .values_list('demande_id', flat=True))

    contexte = {
        'demandes': page_obj.object_list,
        'page_obj': page_obj,
        'categories': categories,
        'categorie_active': categorie_slug,
        'q': q,
        'budget_min': budget_min,
        'budget_max': budget_max,
        'ville': ville,
        'a_distance_active': a_distance,
        'favoris_ids': favoris_ids,
    }
    # Liens de pagination conservant les filtres actifs (query string GET).
    def url_page(numéro):
        requête = request.GET.copy()
        requête['page'] = numéro
        return '?' + requête.urlencode()
    contexte['page_precedente'] = (
        url_page(page_obj.previous_page_number) if page_obj.has_previous() else None)
    contexte['page_suivante'] = (
        url_page(page_obj.next_page_number) if page_obj.has_next() else None)
    if request.user.role == 'prestataire':
        autorise, utilisees, quota = request.user.peut_proposer()
        contexte.update({
            'autorise': autorise,
            'utilisees': utilisees,
            'quota': quota,
            'prochaine_recharge': request.user.prochaine_recharge(),
        })
    return render(request, 'demandes/catalogue.html', contexte)


@login_required
def basculer_favori(request, pk):
    """Ajoute ou retire une demande des favoris du prestataire (toggle).

    Un prestataire met en favori les demandes qui l'intéressent pour les
    retrouver dans sa page « Mes favoris ».  Re-cocher retire le favori.
    """
    if request.user.role != User.Role.PRESTATAIRE:
        messages.error(request, 'Seul un prestataire peut mettre une demande en favori.')
        return redirect('demandes:catalogue')
    demande = get_object_or_404(Demande, pk=pk, statut=Demande.Statut.EN_COURS)
    favori, cree = FavorisDemande.objects.get_or_create(
        prestataire=request.user, demande=demande)
    if cree:
        messages.success(request, f'« {demande.titre} » ajouté à tes favoris.')
    else:
        favori.delete()
        messages.info(request, f'« {demande.titre} » retiré de tes favoris.')
    destination = request.GET.get('next', '')
    if destination.startswith('/'):
        return redirect(destination)
    return redirect('demandes:catalogue')


@login_required
def mes_favoris(request):
    """Page « Mes favoris » du prestataire : les demandes qu'il a marquées."""
    if request.user.role != User.Role.PRESTATAIRE:
        messages.error(request, 'Seul un prestataire consulte des favoris.')
        return redirect('demandes:catalogue')
    favoris = FavorisDemande.objects.filter(
        prestataire=request.user).select_related('demande__categorie')
    return render(request, 'demandes/mes_favoris.html', {
        'favoris': favoris,
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
    # Signale si la demande est déjà dans les favoris du prestataire.
    favori = False
    if request.user.role == User.Role.PRESTATAIRE:
        favori = FavorisDemande.objects.filter(
            prestataire=request.user, demande=demande).exists()
    return render(request, 'demandes/detail_demande.html', {
        'demande': demande,
        'favori': favori,
    })