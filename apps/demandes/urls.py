from django.urls import path

from . import views

app_name = 'demandes'

urlpatterns = [
    path('publier/', views.creation_demande, name='creation_demande'),
    path('mes-demandes/', views.mes_demandes, name='mes_demandes'),
    path('catalogue/', views.catalogue, name='catalogue'),
    path('demande/<int:pk>/', views.detail_demande, name='detail_demande'),
]