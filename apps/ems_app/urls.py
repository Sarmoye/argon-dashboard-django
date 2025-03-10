# apps/analysis/urls.py
from django.urls import path
from . import views

app_name = 'ems_app'

urlpatterns = [
    path('dashboard', views.dashboard, name='error_dashboard'),
    path('reports/', views.report_error, name='report_error'),
    path('list/', views.error_list, name='error_list'),
    path('errors/', views.error_list, name='error_list'),
    path('errors/report/', views.report_error, name='report_error'),
    path('errors/report/details/', views.report_error_details, name='report_error_details'),
    path('errors/report/ticket/', views.create_error_ticket, name='create_error_ticket'),
    path('errors/detail/<str:reference_id>/', views.error_detail, name='error_detail'),
    path('errors/edit/<str:reference_id>/', views.edit_error_details, name='edit_error_details'),

    # Liste et rapport d'erreur
    path('', views.error_list, name='error_list'),
    path('report/', views.report_error, name='report_error'),
    
    # Détails des erreurs
    path('error/<str:error_id>/', views.error_detail, name='error_detail'),
    path('error/<str:error_id>/edit/', views.edit_error_event, name='edit_error_event'),
    
    # Gestion des types d'erreurs
    path('type/<str:type_id>/', views.error_type_detail, name='error_type_detail'),
    path('type/<str:type_id>/edit/', views.edit_error_type, name='edit_error_type'),
    path('type/<str:type_id>/add-occurrence/', views.add_occurrence, name='add_occurrence'),
    
    # Gestion des tickets
    path('type/<str:type_id>/create-ticket/', views.create_ticket, name='create_ticket'),
    path('ticket/<uuid:ticket_id>/update/', views.update_ticket, name='update_ticket'),
]
