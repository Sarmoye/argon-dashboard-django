# apps/visualization/urls.py
from django.urls import path
from . import views

app_name = 'visualization'

urlpatterns = [
    path('', views.index, name='index'),
]