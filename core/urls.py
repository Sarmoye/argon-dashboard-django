# -*- encoding: utf-8 -*-
"""
Copyright (c) 2019 - present AppSeed.us
"""

from django.contrib import admin
from django.urls import path, include  # add this
from django.shortcuts import redirect

urlpatterns = [
    path('admin/', admin.site.urls),          # Django admin route
    path("authentication/", include("apps.authentication.urls")), # Auth routes - login / register
    path('', lambda request: redirect('authentication/login/', permanent=True)),
    path("home/", include("apps.home.urls")),             # UI Kits Html files
    path("sources/", include("apps.sources_data_app.urls"))
]
