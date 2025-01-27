# apps/analysis/urls.py
from django.urls import path
from . import views

app_name = 'analysis'

urlpatterns = [
    path('', views.index, name='index'),
    path('update-fiche-erreur/', views.update_fiche_erreur, name='update_fiche_erreur'),
]
