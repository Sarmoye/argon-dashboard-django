from django.urls import path
from . import views

app_name = 'sources_home_app'

urlpatterns = [
    path('', views.index, name='sources_home'),
]