# apps/analysis/urls.py
from django.urls import path
from . import views

app_name = 'error_management_systems'

urlpatterns = [
    # Pages principales
    path('errors/', views.home, name='home'),
    
    # ErrorEvent
    path('errors/events/', views.event_list, name='event_list'),
    path('errors/events/create/', views.create_event, name='create_event'),
    path('errors/events/<str:event_id>/', views.event_detail, name='event_detail'),
    
    # ErrorType
    path('errors/error-types/', views.error_type_list, name='error_type_list'),
    path('errors/error-types/<str:error_type_id>/', views.error_type_detail, name='error_type_detail'),
    path('errors/error-types/<str:error_type_id>/edit/', views.edit_error_type, name='edit_error_type'),
    
    # ErrorTicket
    path('errors/tickets/', views.ticket_list, name='ticket_list'),
    path('errors/tickets/<uuid:ticket_id>/', views.ticket_detail, name='ticket_detail'),
    path('errors/tickets/<uuid:ticket_id>/edit/', views.edit_ticket, name='edit_ticket'),
    
    # API AJAX
    path('errors/api/check-error-type/', views.check_error_type_exists, name='check_error_type'),
    path('errors/api/create-error-type/', views.create_error_type_ajax, name='create_error_type_ajax'),
    path('errors/api/create-ticket/', views.create_ticket_ajax, name='create_ticket_ajax'),
]
