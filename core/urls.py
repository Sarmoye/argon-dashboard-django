# -*- encoding: utf-8 -*-
"""
Copyright (c) 2019 - present AppSeed.us
"""

from django.contrib import admin
from django.urls import path, include  # add this
from django.shortcuts import redirect

urlpatterns = [
    path('admin/', admin.site.urls),          # Django admin route
    # Redirect root path to login
    path('', lambda request: redirect('/authentication/login/')), # Auth routes - login / register
    path("home/", include("apps.home.urls")),             # UI Kits Html files
    path("sources/", include("apps.sources_data_app.urls")),
    path("analysis/", include("apps.analysis.urls")),
    path("visualization/", include("apps.visualization.urls")),
    path("irm_dashboard/", include("apps.irm_dashboard.urls")),
    path("errors/", include("apps.error_management_systems.urls")),
]
