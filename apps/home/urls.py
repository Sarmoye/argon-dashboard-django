# -*- encoding: utf-8 -*-
"""
Copyright (c) 2019 - present AppSeed.us
"""

from django.urls import path, re_path
from apps.home import views

app_name = 'home'

urlpatterns = [

    # The home page
    path('', views.index, name='home'),
    path('api/error-evolution', views.get_error_evolution, name='error_evolution'),
    # Matches any html file
    # re_path(r'^.*\.*', views.pages, name='pages'),

]
