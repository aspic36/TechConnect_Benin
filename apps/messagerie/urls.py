from django.urls import path

from . import views

app_name = 'messagerie'

urlpatterns = [
    path('mission/<int:pk>/', views.fil_mission, name='fil'),
]