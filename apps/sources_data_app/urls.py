# apps/sources_data_app/urls.py
from django.urls import path
from . import views

app_name = 'sources_data_app'

urlpatterns = [
    path('', views.index, name='index'),
    path('apply-validation/', views.apply_validation, name='apply_validation'),
]
