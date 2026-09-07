from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from .forms import DemandeForm
from .models import Categorie, Demande


@login_required
def creation_demande(request):
    if request.user.role != 'client':
        messages.error(request, 'Seul un client peut publier une demande.')
        return redirect('demandes:catalogue')
    if request.method == 'POST':
        form = DemandeForm(request.POST)
        if form.is_valid():
            demande = form.save(commit=False)
            demande.client = request.user
            demande.save()
            messages.success(request, 'Ta demande a été publiée en attente de validation.')
            return redirect('demandes:mes_demandes')
    else:
        form = DemandeForm()
    return render(request, 'demandes/creation_demande.html', {'form': form})


@login_required
def mes_demandes(request):
    demandes = Demande.objects.filter(client=request.user)
    return render(request, 'demandes/mes_demandes.html', {'demandes': demandes})


@login_required
def catalogue(request):
    demandes = Demande.objects.filter(statut=Demande.Statut.EN_COURS)
    categorie_slug = request.GET.get('categorie')
    q = request.GET.get('q')
    if categorie_slug:
        demandes = demandes.filter(categorie__slug=categorie_slug)
    if q:
        demandes = demandes.filter(Q(titre__icontains=q) | Q(description__icontains=q))
    categories = Categorie.objects.all()
    return render(request, 'demandes/catalogue.html', {
        'demandes': demandes,
        'categories': categories,
        'categorie_active': categorie_slug,
    })


@login_required
def detail_demande(request, pk):
    demande = get_object_or_404(Demande, pk=pk)
    est_proprietaire = demande.client == request.user
    est_prestataire_public = (
        request.user.role == 'prestataire' and demande.statut == Demande.Statut.EN_COURS
    )
    if not (est_proprietaire or est_prestataire_public):
        messages.error(request, 'Cette demande n\'est pas publique.')
        return redirect('demandes:mes_demandes')
    return render(request, 'demandes/detail_demande.html', {'demande': demande})