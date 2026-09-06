from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('apps.accounts.urls')),
    path('demandes/', include('apps.demandes.urls')),
    path('propositions/', include('apps.propositions.urls')),
    path('messagerie/', include('apps.messagerie.urls')),
    path('back-office/', include('apps.admin_panel.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)