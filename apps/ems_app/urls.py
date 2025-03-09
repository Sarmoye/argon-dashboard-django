# apps/analysis/urls.py
from django.urls import path
from . import views

app_name = 'ems_app'

urlpatterns = [
    path('', views.dashboard, name='error_dashboard'),
    path('report/', views.report_error, name='report_error'),
    path('list/', views.error_list, name='error_list'),
    path('detail/<str:reference_id>/', views.error_detail, name='error_detail'),
    path('errors/', views.error_list, name='error_list'),
    path('errors/report/', views.report_error, name='report_error'),
    path('errors/report/details/', views.report_error_details, name='report_error_details'),
    path('errors/report/ticket/', views.create_error_ticket, name='create_error_ticket'),
    path('errors/detail/<str:reference_id>/', views.error_detail, name='error_detail'),
    path('errors/edit/<str:reference_id>/', views.edit_error_details, name='edit_error_details'),
]
