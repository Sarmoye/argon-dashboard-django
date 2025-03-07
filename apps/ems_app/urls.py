# apps/analysis/urls.py
from django.urls import path
from . import views

app_name = 'ems_app'

urlpatterns = [
    path('report/', views.report_error, name='report_error'),
    path('list/', views.error_list, name='error_list'),
    path('detail/<str:reference_id>/', views.error_detail, name='error_detail'),
]
