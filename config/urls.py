"""
URLs racine du projet TechConnect Bénin.

Ce module définit le routeur principal de l'application. Chaque préfixe d'URL
pointe vers un module d'URLs d'une application métier :

  - / (racine)   → apps.accounts   : inscription, connexion, profil
  - /demandes/    → apps.demandes   : publication et consultation de demandes
  - /propositions/→ apps.propositions: soumission de propositions et missions
  - /messagerie/  → apps.messagerie  : messagerie interne par mission
  - /back-office/ → apps.admin_panel : back-office administratif
  - /admin/       → Django Admin natif (pour le superutilisateur)

En mode développement (DEBUG=True), les fichiers médias (avatars, uploads)
sont servis directement par Django via le handler static.
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    # Interface d'administration Django (superutilisateur)
    path('admin/', admin.site.urls),
    # Pages d'authentification et profil (racine du site)
    path('', include('apps.accounts.urls')),
    # Gestion des demandes informatiques (clients)
    path('demandes/', include('apps.demandes.urls')),
    # Propositions de prestataires et missions
    path('propositions/', include('apps.propositions.urls')),
    # Messagerie sécurisée entre client et prestataire
    path('messagerie/', include('apps.messagerie.urls')),
    # Back-office : stats, vérification prestataires, modération
    path('back-office/', include('apps.admin_panel.urls')),
]

# En mode développement, Django sert les fichiers médias (uploads)
# via le handler static pour éviter de configurer un serveur dédié.
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)