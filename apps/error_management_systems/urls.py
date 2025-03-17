# apps/analysis/urls.py
from django.urls import path
from . import views

app_name = 'error_management_systems'

urlpatterns = [
    # Pages principales
    path('', views.home, name='home'),
    
    # ErrorEvent
    path('events/', views.event_list, name='event_list'),
    path('events/create/', views.create_event, name='create_event'),
    path('events/<str:event_id>/', views.event_detail, name='event_detail'),
    
    # ErrorType
    path('error-types/', views.error_type_list, name='error_type_list'),
    path('error-types/<str:error_type_id>/', views.error_type_detail, name='error_type_detail'),
    path('error-types/<str:error_type_id>/edit/', views.edit_error_type, name='edit_error_type'),
    
    # ErrorTicket
    path('tickets/', views.ticket_list, name='ticket_list'),
    path('tickets/<uuid:ticket_id>/', views.ticket_detail, name='ticket_detail'),
    path('tickets/<uuid:ticket_id>/edit/', views.edit_ticket, name='edit_ticket'),
    
    # API AJAX
    path('api/check-error-type/', views.check_error_type_exists, name='check_error_type'),
    path('api/create-error-type/', views.create_error_type_ajax, name='create_error_type_ajax'),
    path('api/create-ticket/', views.create_ticket_ajax, name='create_ticket_ajax'),
]
