from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.contrib import messages
from django.db.models import Count, Sum, Q
from django.utils import timezone
from django.views.decorators.http import require_POST, require_http_methods
import json
from django.contrib.auth.decorators import login_required
from .models import *
from .forms import ErrorTypeForm, ErrorEventForm, ErrorTicketForm
from django.db.models.functions import TruncDate
from django.db import transaction
from django.contrib.auth.decorators import user_passes_test
from django.http import HttpResponseForbidden

def check_user_role(user, allowed_roles=None):
    """
    Check if user has specified role(s).
    
    Args:
        user: Django user object
        allowed_roles: List of allowed roles (optional)
    
    Returns:
        Boolean indicating if user has allowed role
    """
    if not user.is_authenticated:
        return False
    
    # If no roles specified, return True for authenticated user
    if allowed_roles is None:
        return True
    
    return user.role in allowed_roles

# Page d'accueil
from django.shortcuts import render
from django.db.models import Count, Q
from django.db.models.functions import TruncDate
from django.http import HttpResponseForbidden
from django.contrib.auth.decorators import login_required
from .models import ErrorType, ErrorEvent, ErrorTicket, System, Service, ErrorCategory
from django.utils import timezone

@login_required(login_url='/authentication/login/')
def dashboard1(request):
    allowed_roles = ['superadmin', 'admin', 'analyst', 'viewer']
    
    if not check_user_role(request.user, allowed_roles):
        return HttpResponseForbidden("You do not have permission to access this page.")
    
    # Error Type Overview (Widget 1)
    total_error_types = ErrorType.objects.count()
    error_type_categories = list(ErrorType.objects.values('category__name').annotate(count=Count('id')).values_list('category__name', 'count'))
    error_type_impact_levels = list(ErrorType.objects.values('category__severity_level').annotate(count=Count('id')).values_list('category__severity_level', 'count'))
    expected_vs_unexpected = list(ErrorType.objects.values('detected_by').annotate(count=Count('id')).values_list('detected_by', 'count'))

    # Error Type List (Widget 2)
    error_types = ErrorType.objects.order_by('-first_occurrence')[:10]

    # Error Event Overview (Widget 3)
    total_error_events = ErrorEvent.objects.count()
    error_events_time_series = list(
        ErrorEvent.objects.annotate(date=TruncDate('timestamp')).values('date').annotate(count=Count('id')).values_list('date', 'count').order_by('date')
    )
    top_systems_events = list(ErrorEvent.objects.values('system__name').annotate(count=Count('id')).order_by('-count')[:5])
    top_services_events = list(ErrorEvent.objects.values('service__name').annotate(count=Count('id')).order_by('-count')[:5])

    # Error Event List (Widget 4)
    error_events = ErrorEvent.objects.order_by('-timestamp')[:10]

    # Error Ticket Overview (Widget 5)
    total_error_tickets = ErrorTicket.objects.count()
    error_ticket_statuses = list(ErrorTicket.objects.values('status').annotate(count=Count('id')).values_list('status', 'count'))
    error_ticket_priorities = list(ErrorTicket.objects.values('priority').annotate(count=Count('id')).values_list('priority', 'count'))

    # Calculate average ticket resolution time
    resolved_tickets = ErrorTicket.objects.filter(status='RESOLVED', resolved_at__isnull=False)
    if resolved_tickets.exists():
        total_duration = sum([(ticket.resolved_at - ticket.created_at).total_seconds() for ticket in resolved_tickets])
        average_resolution_time = total_duration / resolved_tickets.count() / 3600  # in hours
    else:
        average_resolution_time = 0

    # Error Ticket List (Widget 8)
    error_tickets = ErrorTicket.objects.order_by('-created_at')[:10]

    # Additional Insights
    most_error_prone_system = ErrorEvent.objects.values('system__name').annotate(count=Count('id')).order_by('-count').first()
    most_error_prone_service = ErrorEvent.objects.values('service__name').annotate(count=Count('id')).order_by('-count').first()
    most_common_errors = ErrorType.objects.values('error_description').annotate(count=Count('error_description')).order_by('-count')[:5]
    most_impactful_systems = ErrorType.objects.filter(category__severity_level__in=[3, 4]).values('system__name').annotate(count=Count('id')).order_by('-count')[:5]
    top_impacted_components = ErrorType.objects.exclude(error_metadata__source_component="").values('error_metadata__source_component').annotate(count=Count('id')).order_by('-count')[:5]
    open_tickets = ErrorTicket.objects.filter(status__in=['OPEN', 'IN_PROGRESS']).count()
    recent_events = ErrorEvent.objects.order_by('-timestamp')[:5]
    top_errors = ErrorType.objects.annotate(event_count=Count('events')).order_by('-event_count')[:5]
    critical_tickets = ErrorTicket.objects.filter(priority='P1', status__in=['OPEN', 'IN_PROGRESS']).order_by('created_at')[:5]

    context = {
        'total_error_types': total_error_types,
        'error_type_categories': error_type_categories,
        'error_type_impact_levels': error_type_impact_levels,
        'expected_vs_unexpected': expected_vs_unexpected,
        'error_types': error_types,
        'total_error_events': total_error_events,
        'error_events_time_series': error_events_time_series,
        'top_systems_events': top_systems_events,
        'top_services_events': top_services_events,
        'error_events': error_events,
        'total_error_tickets': total_error_tickets,
        'error_ticket_statuses': error_ticket_statuses,
        'error_ticket_priorities': error_ticket_priorities,
        'average_resolution_time': average_resolution_time,
        'error_tickets': error_tickets,
        'open_tickets': open_tickets,
        'recent_events': recent_events,
        'top_errors': top_errors,
        'critical_tickets': critical_tickets,
        'most_error_prone_system': most_error_prone_system,
        'most_error_prone_service': most_error_prone_service,
        'most_common_errors': most_common_errors,
        'most_impactful_systems': most_impactful_systems,
        'top_impacted_components': top_impacted_components,
    }

    return render(request, 'error_management_systems/dashboard1.html', {'context': context})



@login_required(login_url='/authentication/login/')
def dashboard2(request):
    allowed_roles = ['superadmin', 'admin', 'analyst', 'viewer']
    
    if not check_user_role(request.user, allowed_roles):
        return HttpResponseForbidden("You do not have permission to access this page.")
    
    """View to render error events time series chart with dynamic filtering."""

    # Additional System Insights
    most_error_prone_system = ErrorEvent.objects.values('system__name').annotate(count=Count('id')).order_by('-count').first()
    most_error_prone_service = ErrorEvent.objects.values('service__name').annotate(count=Count('id')).order_by('-count').first()
    most_error_prone_system_class = ErrorEvent.objects.values('system__system_classification').annotate(count=Count('id')).order_by('-count').first()
    most_error_prone_service_class = ErrorEvent.objects.values('service__service_classification').annotate(count=Count('id')).order_by('-count').first()

    most_common_errors = ErrorEvent.objects.values('error_type__error_description').annotate(count=Count('id')).order_by('-count')[:10]

    critical_counts = ErrorType.objects.filter(category__severity_level__in=[3, 4]).count()
    non_critical_counts = ErrorType.objects.filter(category__severity_level__in=[1, 2]).count()

    most_impactful_systems = (
        ErrorType.objects.filter(category__severity_level__in=[3, 4])
        .values('system__name')
        .annotate(count=Count('id'))
        .order_by('-count')[:5]
    )

    most_impactful_systems_class = (
        ErrorType.objects.filter(category__severity_level__in=[3, 4])
        .values('system__system_classification')
        .annotate(count=Count('id'))
        .order_by('-count')[:5]
    )

    top_impacted_services = (
        ErrorType.objects
        .filter(category__severity_level__in=[3, 4])
        .exclude(service__name="")
        .values('service__name')
        .annotate(count=Count('id'))
        .order_by('-count')[:5]
    )

    top_impacted_services_class = (
        ErrorType.objects
        .filter(category__severity_level__in=[3, 4])
        .exclude(service__service_classification="")
        .values('service__service_classification')
        .annotate(count=Count('id'))
        .order_by('-count')[:5]
    )

    # Start with base queryset
    queryset = ErrorEvent.objects.all()
    
    # Extract filter parameters from GET request
    system_name = request.GET.get('system_name')
    system_classification = request.GET.get('system_classification')
    service_name = request.GET.get('service_name')
    service_classification = request.GET.get('service_classification')
    
    # Apply filters based on provided parameters
    if system_name:
        queryset = queryset.filter(system__name=system_name)
    
    if system_classification:
        queryset = queryset.filter(system__system_classification=system_classification)
    
    if service_name:
        queryset = queryset.filter(service__name=service_name)
    
    if service_classification:
        queryset = queryset.filter(service__service_classification=service_classification)
    
    # Aggregate error events by date
    error_events_time_series = (
        queryset
        .annotate(date=TruncDate('timestamp'))
        .values('date')
        .annotate(count=Count('id'))
        .order_by('date')
    )
    
    # Prepare data for chart
    dates = [entry['date'].strftime('%Y-%m-%d') for entry in error_events_time_series]
    counts = [entry['count'] for entry in error_events_time_series]
    
    # Get unique filter options
    unique_systems = System.objects.values_list('name', flat=True).distinct()
    unique_system_classifications = System.objects.values_list('system_classification', flat=True).distinct()
    unique_services = Service.objects.values_list('name', flat=True).distinct()
    unique_service_classifications = Service.objects.values_list('service_classification', flat=True).distinct()

    context = {
        # Systems Insights
        'most_error_prone_system': most_error_prone_system,
        'most_error_prone_service': most_error_prone_service,
        'most_error_prone_system_class': most_error_prone_system_class,
        'most_error_prone_service_class': most_error_prone_service_class,

        'most_common_errors': most_common_errors,
        'most_impactful_systems': most_impactful_systems,
        'most_impactful_systems_class': most_impactful_systems_class,
        'top_impacted_services': top_impacted_services,
        'top_impacted_services_class': top_impacted_services_class,
        'critical_counts': critical_counts,
        'non_critical_counts': non_critical_counts,

        'dates': dates,
        'counts': counts,
        'unique_systems': unique_systems,
        'unique_system_classifications': unique_system_classifications,
        'unique_services': unique_services,
        'unique_service_classifications': unique_service_classifications,
        
        # Retain selected filters for form persistence
        'selected_system': system_name,
        'selected_system_classification': system_classification,
        'selected_service': service_name,
        'selected_service_classification': service_classification,
    }

    return render(request, 'error_management_systems/dashboard2.html', context)


# ---- ErrorEvent Views ----
@login_required(login_url='/authentication/login/')
def event_list(request):
    allowed_roles = ['superadmin', 'admin', 'analyst', 'viewer']
    
    if not check_user_role(request.user, allowed_roles):
        return HttpResponseForbidden("You do not have permission to access this page.")
    
    """Liste des événements d'erreur avec filtres"""
    events = ErrorEvent.objects.all().order_by('-timestamp')
    
    # Filtres récupérés dans l'URL
    system_filter = request.GET.get('system')
    service_filter = request.GET.get('service')
    environment_filter = request.GET.get('environment')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    
    if system_filter:
        # Filtrage sur le nom du système via la relation
        events = events.filter(system__name__icontains=system_filter)
    if service_filter:
        # Filtrage sur le nom du service via la relation
        events = events.filter(service__name__icontains=service_filter)
    if environment_filter:
        events = events.filter(environment=environment_filter)
    if date_from:
        events = events.filter(timestamp__gte=date_from)
    if date_to:
        events = events.filter(timestamp__lte=date_to)
    
    # Récupération des filtres pour l'affichage
    systems = System.objects.all()
    services = Service.objects.all()
    # Liste des environnements basée sur les choix définis dans le modèle
    environments = ['development', 'staging', 'production', 'testing']
    
    context = {
        'events': events,
        'systems': systems,
        'services': services,
        'environments': environments,
    }
    
    return render(request, 'error_management_systems/event_list.html', context)

@login_required(login_url='/authentication/login/')
def event_detail(request, event_id):
    allowed_roles = ['superadmin', 'admin', 'analyst', 'viewer']
    
    if not check_user_role(request.user, allowed_roles):
        return HttpResponseForbidden("You do not have permission to access this page.")
    
    """Détail d'un événement d'erreur"""
    event = get_object_or_404(ErrorEvent, event_id=event_id)
    related_events = ErrorEvent.objects.filter(error_type=event.error_type).exclude(event_id=event_id).order_by('-timestamp')[:5]
    
    # Vérifier si un ticket existe pour ce type d'erreur
    try:
        ticket = event.error_type.tickets.first()
        has_ticket = True
    except ErrorTicket.DoesNotExist:
        ticket = None
        has_ticket = False
    
    context = {
        'event': event,
        'related_events': related_events,
        'ticket': ticket,
        'has_ticket': has_ticket
    }
    
    return render(request, 'error_management_systems/event_detail.html', context)

@login_required(login_url='/authentication/login/')
def create_event(request):
    allowed_roles = ['superadmin', 'admin', 'analyst']
    
    if not check_user_role(request.user, allowed_roles):
        return HttpResponseForbidden("You do not have permission to access this page.")
    
    if request.method == 'POST':
        try:
            with transaction.atomic():
                # 1. Vérification et création du Système si nécessaire
                system, system_created = System.objects.get_or_create(
                    name=request.POST.get('system_name'),
                    defaults={
                        'system_classification': request.POST.get('system_classification', ''),
                        'description': request.POST.get('system_description', '')
                    }
                )

                # 2. Vérification et création du Service si nécessaire
                service, service_created = Service.objects.get_or_create(
                    system=system,
                    name=request.POST.get('service_name'),
                    defaults={
                        'service_classification': request.POST.get('service_classification', ''),
                        'description': request.POST.get('service_description', ''),
                        'owner': request.user.username
                    }
                )

                # 3. Vérification et création de la Catégorie d'Erreur si nécessaire
                error_category, category_created = ErrorCategory.objects.get_or_create(
                    name=request.POST.get('error_category_name'),
                    defaults={
                        'description': request.POST.get('error_category_description', ''),
                        'severity_level': request.POST.get('severity_level', 2)
                    }
                )

                # 4. Vérification de l'existence et création de l'ErrorType
                error_type = ErrorType.objects.filter(error_description=request.POST.get('error_description')).first()

                if error_type:
                    error_type.is_active = True
                    error_type.save()
                else:
                    # Créer un nouveau TYpe
                    error_type = ErrorType.objects.create(
                        system=system,
                        service=service,
                        category=error_category,
                        error_description= request.POST.get('error_description', ''),
                        root_cause= request.POST.get('root_cause', ''),
                        is_active= True,
                        detected_by= request.POST.get('detected_by', 'logs'),
                        error_source= request.POST.get('error_source', 'internal'),
                        total_occurrences=0,
                    )

                # 5. Création de l'ErrorEvent
                error_event = ErrorEvent.objects.create(
                    error_type=error_type,
                    system=system,
                    service=service,
                    error_count=request.POST.get('error_count', ''),
                    event_log=request.POST.get('event_log', ''),
                    source_ip=request.POST.get('source_ip', ''),
                    trigger_event=request.POST.get('trigger_event', ''),
                    environment=request.POST.get('environment', 'production'),
                    inserted_by=request.user.username,
                )

                # 6. Gestion du ticket d'erreur
                # Vérifier si un ticket avec le même numéro d'erreur existe
                error_ticket = ErrorTicket.objects.filter(ticket_number=error_type.error_code).first()

                if error_ticket:
                    # Réouvrir le ticket existant
                    error_ticket.status = 'OPEN'
                    error_ticket.save()
                else:
                    # Créer un nouveau ticket
                    error_ticket = ErrorTicket.objects.create(
                        error_type=error_type,
                        status='OPEN',
                        priority=request.POST.get('priority', 'P3'),
                        title=f"Error Event {error_event.event_id}",
                        description=error_type.error_description,
                        root_cause= request.POST.get('root_cause', ''),
                        assigned_to=request.user.username
                    )

                messages.success(request, f"Événement d'erreur créé avec succès: {error_event.event_id}")
                return redirect('error_management_systems:event_detail', event_id=error_event.event_id)

        except Exception as e:
            messages.error(request, f"Erreur lors de la création de l'événement: {str(e)}")
            import logging
            logging.exception("Erreur durant create_event")
            return redirect('error_management_systems:create_event')

    # Préparation du contexte pour le formulaire GET
    context = {
        'systems': System.objects.all(),
        'services': Service.objects.all(),
        'error_categories': ErrorCategory.objects.all(),
        'detected_by_choices': ErrorType._meta.get_field('detected_by').choices,
        'error_source_choices': ErrorType._meta.get_field('error_source').choices,
        'environment_choices': ErrorEvent._meta.get_field('environment').choices,
    }

    return render(request, 'error_management_systems/create_event.html', context)


@login_required(login_url='/authentication/login/')
def modify_error_type_details(request, event_id, error_type_id):
    allowed_roles = ['superadmin', 'admin', 'analyst']
    
    if not check_user_role(request.user, allowed_roles):
        return HttpResponseForbidden("You do not have permission to access this page.")
    
    """Modifier les détails du type d'erreur après la création de l'événement"""
    error_type = get_object_or_404(ErrorType, id=error_type_id)
    event = get_object_or_404(ErrorEvent, id=event_id)
    
    if request.method == 'POST':
        form = ErrorTypeForm(request.POST, instance=error_type)
        if form.is_valid():
            form.save()
            messages.success(request, f"Type d'erreur mis à jour: {error_type.id}")
            return redirect('error_management_systems:event_detail', event_id=event.id)
    else:
        form = ErrorTypeForm(instance=error_type)
    
    context = {
        'form': form,
        'error_type': error_type,
        'event': event
    }
    
    return render(request, 'error_management_systems/edit_error_type.html', context)

@login_required(login_url='/authentication/login/')
def modify_error_ticket_details(request, event_id, error_type_id):
    allowed_roles = ['superadmin', 'admin', 'analyst']
    
    if not check_user_role(request.user, allowed_roles):
        return HttpResponseForbidden("You do not have permission to access this page.")
    
    """Modifier les détails du ticket après la création de l'événement"""
    error_type = get_object_or_404(ErrorType, id=error_type_id)
    event = get_object_or_404(ErrorEvent, id=event_id)
    ticket = get_object_or_404(ErrorTicket, error_type=error_type)
    
    if request.method == 'POST':
        form = ErrorTicketForm(request.POST, instance=ticket)
        if form.is_valid():
            form.save()
            messages.success(request, f"Ticket mis à jour: {ticket.ticket_reference}")
            return redirect('error_management_systems:event_detail', event_id=event.id)
    else:
        form = ErrorTicketForm(instance=ticket)
    
    context = {
        'form': form,
        'ticket': ticket,
        'error_type': error_type,
        'event': event
    }
    
    return render(request, 'error_management_systems/edit_ticket.html', context)

# ---- ErrorType Views ----
@login_required(login_url='/authentication/login/')
def error_type_list(request):
    allowed_roles = ['superadmin', 'admin', 'analyst', 'viewer']
    
    if not check_user_role(request.user, allowed_roles):
        return HttpResponseForbidden("You do not have permission to access this page.")
    
    """Liste des types d'erreurs avec filtres et statistiques"""
    error_types = ErrorType.objects.annotate(event_count=Count('total_occurrences')).order_by('-event_count')
    
    # Filtres
    system_filter = request.GET.get('system')
    service_filter = request.GET.get('service')
    category_filter = request.GET.get('category')
    
    if system_filter:
        error_types = error_types.filter(system__name__icontains=system_filter)
    if service_filter:
        error_types = error_types.filter(service__name__icontains=service_filter)
    if category_filter:
        error_types = error_types.filter(category__name__icontains=category_filter)
    
    # Liste des systèmes, services et catégories pour les filtres
    systems = System.objects.values_list('name', flat=True).distinct()
    services = Service.objects.values_list('name', flat=True).distinct()
    categories = ErrorType.objects.values_list('category__name', flat=True).distinct()
    
    context = {
        'error_types': error_types,
        'systems': systems,
        'services': services,
        'categories': categories,
    }
    
    return render(request, 'error_management_systems/error_type_list.html', context)


@login_required(login_url='/authentication/login/')
def error_type_detail(request, error_type_id):
    allowed_roles = ['superadmin', 'admin', 'analyst', 'viewer']
    
    if not check_user_role(request.user, allowed_roles):
        return HttpResponseForbidden("You do not have permission to access this page.")
    
    """Détail d'un type d'erreur avec ses événements associés"""
    error_type = get_object_or_404(ErrorType, id=error_type_id)
    events = error_type.events.all().order_by('-timestamp')
    
    # Vérifier si un ticket existe
    try:
        ticket = error_type.tickets.first()
        has_ticket = True
    except ErrorTicket.DoesNotExist:
        ticket = None
        has_ticket = False
    
    context = {
        'error_type': error_type,
        'events': events,
        'event_count': events.count(),
        'total_errors': events.aggregate(Sum('error_count'))['error_count__sum'] or 0,
        'ticket': ticket,
        'has_ticket': has_ticket
    }
    
    return render(request, 'error_management_systems/error_type_detail.html', context)

@login_required(login_url='/authentication/login/')
def edit_error_type(request, error_type_id):
    allowed_roles = ['superadmin', 'admin', 'analyst']
    
    if not check_user_role(request.user, allowed_roles):
        return HttpResponseForbidden("You do not have permission to access this page.")
    
    """Édition d'un type d'erreur"""
    error_type = get_object_or_404(ErrorType, id=error_type_id)
    
    if request.method == 'POST':
        form = ErrorTypeForm(request.POST, instance=error_type)
        if form.is_valid():
            form.save()
            messages.success(request, f"Type d'erreur mis à jour: {error_type.id}")
            return redirect('error_management_systems:error_type_detail', error_type_id=error_type.id)
    else:
        form = ErrorTypeForm(instance=error_type)
    
    context = {
        'form': form,
        'error_type': error_type
    }
    
    return render(request, 'error_management_systems/edit_error_type.html', context)

# ---- ErrorTicket Views ----
@login_required(login_url='/authentication/login/')
def ticket_list(request):
    allowed_roles = ['superadmin', 'admin', 'analyst', 'viewer']
    
    if not check_user_role(request.user, allowed_roles):
        return HttpResponseForbidden("You do not have permission to access this page.")
    
    """Liste des tickets avec filtres"""
    tickets = ErrorTicket.objects.all().order_by('-created_at')
    
    # Filtres
    status_filter = request.GET.get('status')
    priority_filter = request.GET.get('priority')
    system_filter = request.GET.get('system')
    
    if status_filter:
        tickets = tickets.filter(status=status_filter)
    if priority_filter:
        tickets = tickets.filter(priority=priority_filter)
    if system_filter:
        tickets = tickets.filter(error_type__system__name__icontains=system_filter)
    
    # Données pour les filtres
    systems = System.objects.values_list('name', flat=True).distinct()
    
    context = {
        'tickets': tickets,
        'systems': systems,
        'status_choices': ErrorTicket.STATUS_CHOICES,
        'priority_choices': ErrorTicket.PRIORITY_CHOICES
    }
    
    return render(request, 'error_management_systems/ticket_list.html', context)


@login_required(login_url='/authentication/login/')
def ticket_detail(request, ticket_id):
    allowed_roles = ['superadmin', 'admin', 'analyst', 'viewer']
    
    if not check_user_role(request.user, allowed_roles):
        return HttpResponseForbidden("You do not have permission to access this page.")
    
    """Détail d'un ticket"""
    ticket = get_object_or_404(ErrorTicket, id=ticket_id)
    events = ticket.error_type.events.all().order_by('-timestamp')
    
    context = {
        'ticket': ticket,
        'error_type': ticket.error_type,
        'events': events,
        'event_count': events.count(),
        'total_errors': events.aggregate(Sum('error_count'))['error_count__sum'] or 0,
        'ticket_duration': ticket.calculate_resolution_time()
    }
    
    return render(request, 'error_management_systems/ticket_detail.html', context)

@login_required(login_url='/authentication/login/')
def edit_ticket(request, ticket_id):
    allowed_roles = ['superadmin', 'admin', 'analyst']
    
    if not check_user_role(request.user, allowed_roles):
        return HttpResponseForbidden("You do not have permission to access this page.")
    
    ticket = get_object_or_404(ErrorTicket, id=ticket_id)
    
    if request.method == 'POST':
        form = ErrorTicketForm(request.POST, instance=ticket)
        if form.is_valid():
            # Capture previous state for history
            old_status = ticket.status
            old_priority = ticket.priority
            
            # Save modifications without committing immediately
            updated_ticket = form.save(commit=False)
            
            # Log changes in status and priority if they differ
            if old_status != updated_ticket.status or old_priority != updated_ticket.priority:
                timestamp = timezone.now().isoformat()
                change_record = {
                    'timestamp': timestamp,
                    'status_change': {
                        'from': old_status,
                        'to': updated_ticket.status
                    } if old_status != updated_ticket.status else None,
                    'priority_change': {
                        'from': old_priority,
                        'to': updated_ticket.priority
                    } if old_priority != updated_ticket.priority else None
                }
                # Append the change record to the modification history
                modification_history = updated_ticket.modification_history or []
                modification_history.append(change_record)
                updated_ticket.modification_history = modification_history
            
            # Save the ticket (the model's save method will also handle logging status changes)
            updated_ticket.save()
            messages.success(request, f"Ticket mis à jour: {ticket.ticket_number}")
            return redirect('error_management_systems:ticket_detail', ticket_id=ticket.id)
    else:
        form = ErrorTicketForm(instance=ticket)
    
    context = {
        'form': form,
        'ticket': ticket,
        'error_type': ticket.error_type
    }
    
    return render(request, 'error_management_systems/edit_ticket.html', context)

# ---- API Views ----
from rest_framework import status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from django.contrib.auth import authenticate
from .models import ErrorEvent, ErrorType, ErrorTicket
from .serializers import ErrorEventSerializer
from rest_framework.throttling import UserRateThrottle
from django.db import transaction
from django.db.models import F
from django.core.cache import cache
import logging

logger = logging.getLogger(__name__)

class CustomUserRateThrottle(UserRateThrottle):
    rate = '150/minute'  # Increased to accommodate 100+ requests per minute with buffer

@api_view(['POST'])
def get_auth_token(request):
    """API endpoint to obtain an authentication token."""
    username = request.data.get('username')
    password = request.data.get('password')

    if not username or not password:
        return Response({'error': 'Please provide username and password.'}, status=status.HTTP_400_BAD_REQUEST)

    user = authenticate(username=username, password=password)

    if user:
        token, created = Token.objects.get_or_create(user=user)
        return Response({'token': token.key})
    else:
        return Response({'error': 'Invalid credentials.'}, status=status.HTTP_401_UNAUTHORIZED)



@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def create_event_api(request):
    """API endpoint to create a new error event with optimizations for high volume."""
    throttle_classes = [CustomUserRateThrottle]
        
    # Support both single event and batch processing
    events_data = request.data
    if not isinstance(events_data, list):
        events_data = [events_data]
        
    # Validate all entries before processing
    for event_data in events_data:
        required_fields = ['system_name', 'service_name', 'error_category_name', 'error_description']
        if not all(field in event_data for field in required_fields):
            return Response({"error": "Missing required fields in one or more entries."}, 
                           status=status.HTTP_400_BAD_REQUEST)
    
    results = []
    failed_entries = []
    
    for event_data in events_data:
        try:
            with transaction.atomic():
                # Use select_for_update to prevent race conditions when multiple requests 
                # try to update the same system/service
                
                # 1. System creation/update with get_or_create for atomicity
                system, _ = System.objects.select_for_update().get_or_create(
                    name=event_data.get('system_name'),
                    defaults={
                        'system_classification': event_data.get('system_classification', ''),
                        'description': event_data.get('system_description', '')
                    }
                )

                # 2. Service creation/update
                service, _ = Service.objects.select_for_update().get_or_create(
                    system=system,
                    name=event_data.get('service_name'),
                    defaults={
                        'service_classification': event_data.get('service_classification', ''),
                        'description': event_data.get('service_description', ''),
                        'owner': request.user.username
                    }
                )

                # 3. ErrorCategory creation/update
                error_category, _ = ErrorCategory.objects.select_for_update().get_or_create(
                    name=event_data.get('error_category_name'),
                    defaults={
                        'description': event_data.get('error_category_description', ''),
                        'severity_level': event_data.get('severity_level', 2)
                    }
                )

                # 4. Optimize ErrorType lookup and update
                # Use a more optimized query with select_for_update
                try:
                    error_type = ErrorType.objects.select_for_update().get(
                        error_description=event_data.get('error_description')
                    )
                    # Use F() expressions to avoid race conditions in concurrent updates
                    ErrorType.objects.filter(pk=error_type.pk).update(
                        is_active=True,
                        total_occurrences=F('total_occurrences') + int(event_data.get('error_count', 1))
                    )
                    # Refresh from database to get updated values
                    error_type.refresh_from_db()
                except ErrorType.DoesNotExist:
                    # Create new ErrorType
                    error_type = ErrorType.objects.create(
                        system=system,
                        service=service,
                        category=error_category,
                        error_description=event_data.get('error_description', ''),
                        root_cause=event_data.get('root_cause', ''),
                        is_active=True,
                        detected_by=event_data.get('detected_by', 'logs'),
                        error_source=event_data.get('error_source', 'internal'),
                        total_occurrences=int(event_data.get('error_count', 1)),
                    )

                # 5. ErrorEvent creation - use bulk_create for multiple events if needed
                error_event = ErrorEvent.objects.create(
                    error_type=error_type,
                    system=system,
                    service=service,
                    error_count=event_data.get('error_count', 1),
                    event_log=event_data.get('event_log', ''),
                    source_ip=event_data.get('source_ip', ''),
                    trigger_event=event_data.get('trigger_event', ''),
                    environment=event_data.get('environment', 'production')
                )

                # 6. ErrorTicket management - optimize with select_for_update
                error_ticket = None
                try:
                    error_ticket = ErrorTicket.objects.select_for_update().get(
                        ticket_number=error_type.error_code
                    )
                    # Update ticket status if it's not already open
                    if error_ticket.status != 'OPEN':
                        error_ticket.status = 'OPEN'
                        error_ticket.save(update_fields=['status'])
                except ErrorTicket.DoesNotExist:
                    # Create new ticket
                    error_ticket = ErrorTicket.objects.create(
                        error_type=error_type,
                        status='OPEN',
                        priority=event_data.get('priority', 'P3'),
                        title=f"Error Event {error_event.event_id}",
                        description=error_type.error_description,
                        root_cause=event_data.get('root_cause', ''),
                        assigned_to=request.user.username
                    )

                # Add to successful results
                serializer = ErrorEventSerializer(error_event)
                results.append(serializer.data)
                
        except Exception as e:
            logger.exception(f"Error processing event: {event_data.get('error_description', 'Unknown')}")
            failed_entries.append({
                "data": event_data,
                "error": str(e)
            })
    
    # Return appropriate response based on results
    if not failed_entries:
        return Response({
            "status": "success",
            "count": len(results),
            "results": results
        }, status=status.HTTP_201_CREATED)
    elif not results:
        return Response({
            "status": "error",
            "message": "All entries failed to process",
            "failed_entries": failed_entries
        }, status=status.HTTP_400_BAD_REQUEST)
    else:
        return Response({
            "status": "partial_success",
            "success_count": len(results),
            "failed_count": len(failed_entries),
            "results": results,
            "failed_entries": failed_entries
        }, status=status.HTTP_207_MULTI_STATUS)