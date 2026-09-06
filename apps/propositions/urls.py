from django.urls import path

from . import views

app_name = 'propositions'

urlpatterns = [
    path('demande/<int:pk>/soumettre/', views.soumettre_proposition, name='soumettre'),
    path('mes-propositions/', views.mes_propositions, name='mes_propositions'),
    path('demande/<int:pk>/propositions/', views.propositions_demande, name='propositions_demande'),
    path('proposition/<int:pk>/accepter/', views.accepter_proposition, name='accepter'),
    path('proposition/<int:pk>/refuser/', views.refuser_proposition, name='refuser'),
    path('missions/', views.liste_missions, name='liste_missions'),
    path('missions/<int:pk>/', views.detail_mission, name='detail_mission'),
    path('missions/<int:pk>/clore/', views.clore_mission, name='clore'),
    path('missions/<int:pk>/evaluer/', views.evaluer_mission, name='evaluer'),
    path('missions/<int:pk>/paiement/', views.enregistrer_paiement, name='paiement'),
]