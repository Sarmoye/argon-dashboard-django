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
@login_required(login_url='/authentication/login/')
def dashboard1(request):
    allowed_roles = ['superadmin', 'admin', 'analyst', 'viewer']
    
    if not check_user_role(request.user, allowed_roles):
        return HttpResponseForbidden("You do not have permission to access this page.")
    
    """Page d'accueil avec statistiques générales et derniers événements"""
    # Error Type Overview (Widget 1)
    total_error_types = ErrorType.objects.count()
    error_type_categories = ErrorType.objects.values('category__name').annotate(count=Count('category'))
    error_type_impact_levels = ErrorType.objects.values('category__severity_level').annotate(count=Count('category__severity_level'))
    expected_vs_unexpected = ErrorType.objects.values('detected_by').annotate(count=Count('detected_by'))

    # Error Type List (Widget 2)
    error_types = ErrorType.objects.order_by('-first_occurrence')[:10]

    # Error Event Overview (Widget 3)
    total_error_events = ErrorEvent.objects.count()
    error_events_time_series = (
        ErrorEvent.objects.annotate(date=TruncDate('timestamp'))
        .values('date')
        .annotate(count=Count('id'))
        .order_by('date')
    )
    
    top_systems_events = (
        ErrorEvent.objects.values('system__name')
        .annotate(count=Count('id'))
        .order_by('-count')[:5]
    )
    top_services_events = (
        ErrorEvent.objects.values('service__name')
        .annotate(count=Count('id'))
        .order_by('-count')[:5]
    )

    # Additional System Insights
    most_error_prone_system = (
        ErrorEvent.objects.values('system__name')
        .annotate(count=Count('id'))
        .order_by('-count')
        .first()
    )
    most_error_prone_service = (
        ErrorEvent.objects.values('service__name')
        .annotate(count=Count('id'))
        .order_by('-count')
        .first()
    )

    most_common_errors = (
        ErrorType.objects.values('error_description')
        .annotate(count=Count('error_description'))
        .order_by('-count')[:5]
    )

    most_impactful_systems = (
        ErrorType.objects.filter(category__severity_level__in=[3, 4])  # High and Critical Severity
        .values('system__name')
        .annotate(count=Count('id'))
        .order_by('-count')[:5]
    )

    top_impacted_components = (
        ErrorType.objects.exclude(error_metadata__source_component="")
        .values('error_metadata__source_component')
        .annotate(count=Count('id'))
        .order_by('-count')[:5]
    )

    # Error Event List (Widget 4)
    error_events = ErrorEvent.objects.order_by('-timestamp')[:10]

    # Error Ticket Overview (Widget 5)
    total_error_tickets = ErrorTicket.objects.count()
    error_ticket_statuses = ErrorTicket.objects.values('status').annotate(count=Count('status'))
    error_ticket_priorities = ErrorTicket.objects.values('priority').annotate(count=Count('priority'))
    
    # Calculate average ticket resolution time
    resolved_tickets = ErrorTicket.objects.filter(status='RESOLVED', resolved_at__isnull=False)
    if resolved_tickets.exists():
        total_duration = sum([(ticket.resolved_at - ticket.created_at).total_seconds() for ticket in resolved_tickets])
        average_resolution_time = total_duration / resolved_tickets.count() / 3600  # in hours
    else:
        average_resolution_time = 0

    # Error Ticket List (Widget 8)
    error_tickets = ErrorTicket.objects.order_by('-created_at')[:10]

    total_error_types = ErrorType.objects.count()
    total_error_events = ErrorEvent.objects.count()
    open_tickets = ErrorTicket.objects.filter(status__in=['OPEN', 'IN_PROGRESS']).count()
    recent_events = ErrorEvent.objects.order_by('-timestamp')[:5]
    top_errors = (
        ErrorType.objects.annotate(event_count=Count('events'))
        .order_by('-event_count')[:5]
    )
    critical_tickets = ErrorTicket.objects.filter(priority='P1', status__in=['OPEN', 'IN_PROGRESS']).order_by('created_at')[:5]

    context = {
        # Widget 1
        'total_error_types': total_error_types,
        'error_type_categories': error_type_categories,
        'error_type_impact_levels': error_type_impact_levels,
        'expected_vs_unexpected': expected_vs_unexpected,
        # Widget 2
        'error_types': error_types,
        # Widget 3
        'total_error_events': total_error_events,
        'error_events_time_series': error_events_time_series,
        'top_systems_events': top_systems_events,
        'top_services_events': top_services_events,
        # Widget 4
        'error_events': error_events,
        # Widget 5
        'total_error_tickets': total_error_tickets,
        'error_ticket_statuses': error_ticket_statuses,
        'error_ticket_priorities': error_ticket_priorities,
        'average_resolution_time': average_resolution_time,
        # Widget 8
        'error_tickets': error_tickets,
        'open_tickets': open_tickets,
        'recent_events': recent_events,
        'top_errors': top_errors,
        'critical_tickets': critical_tickets,

        # New Insights
        'most_error_prone_system': most_error_prone_system,
        'most_error_prone_service': most_error_prone_service,
        'most_common_errors': most_common_errors,
        'most_impactful_systems': most_impactful_systems,
        'top_impacted_components': top_impacted_components,
    }

    # Statistiques globales
    stats = {
        'total_error_types': ErrorType.objects.count(),
        'total_error_events': ErrorEvent.objects.count(),
        'open_tickets': ErrorTicket.objects.filter(status__in=['OPEN', 'IN_PROGRESS']).count(),
        'recent_events': ErrorEvent.objects.order_by('-timestamp')[:5],
        'top_errors': ErrorType.objects.annotate(event_count=Count('events')).order_by('-event_count')[:5],
        'critical_tickets': ErrorTicket.objects.filter(priority='P1', status__in=['OPEN', 'IN_PROGRESS']).order_by('created_at')[:5]
    }
    
    return render(request, 'error_management_systems/dashboard1.html', {'context': context, 'stats': stats})



@login_required(login_url='/authentication/login/')
def dashboard2(request):
    allowed_roles = ['superadmin', 'admin', 'analyst', 'viewer']
    
    if not check_user_role(request.user, allowed_roles):
        return HttpResponseForbidden("You do not have permission to access this page.")
    
    """View to render error events time series chart with dynamic filtering."""

    # Additional System Insights
    most_error_prone_system = ErrorEvent.objects.values('system_name').annotate(count=Count('id')).order_by('-count').first()
    most_error_prone_service = ErrorEvent.objects.values('service_name').annotate(count=Count('id')).order_by('-count').first()
    most_error_prone_system_class = ErrorEvent.objects.values('error_type__system_classification').annotate(count=Count('id')).order_by('-count').first()
    most_error_prone_service_class = ErrorEvent.objects.values('error_type__service_classification').annotate(count=Count('id')).order_by('-count').first()

    most_common_errors = ErrorEvent.objects.values('error_reason').annotate(count=Count('id')).order_by('-count')[:10]

    critical_counts = ErrorType.objects.filter(impact_level__in=['critical', 'high']).count()
    non_critical_counts = ErrorType.objects.filter(impact_level__in=['low', 'medium']).count()

    most_impactful_systems = (
        ErrorType.objects.filter(impact_level__in=['critical', 'high'])
        .values('system_name')
        .annotate(count=Count('id'))
        .order_by('-count')[:5]
    )

    most_impactful_systems_class = (
        ErrorType.objects.filter(impact_level__in=['critical', 'high'])
        .values('system_classification')
        .annotate(count=Count('id'))
        .order_by('-count')[:5]
    )

    top_impacted_services = (
    ErrorType.objects
    .filter(impact_level__in=['critical', 'high'])  # (1) Filter by impact level
    .exclude(service_name="")  # (2) Exclude empty service names
    .values('service_name')  # (3) Group by service_name
    .annotate(count=Count('id'))  # (4) Count occurrences
    .order_by('-count')[:5]  # (5) Order by count (descending) and limit to top 5
    )

    top_impacted_services_class = (
    ErrorType.objects
    .filter(impact_level__in=['critical', 'high'])  # (1) Filter by impact level
    .exclude(service_classification="")  # (2) Exclude empty service names
    .values('service_classification')  # (3) Group by service_name
    .annotate(count=Count('id'))  # (4) Count occurrences
    .order_by('-count')[:5]  # (5) Order by count (descending) and limit to top 5
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
        queryset = queryset.filter(system_name=system_name)
    
    if system_classification:
        queryset = queryset.filter(error_type__system_classification=system_classification)
    
    if service_name:
        queryset = queryset.filter(service_name=service_name)
    
    if service_classification:
        queryset = queryset.filter(error_type__service_classification=service_classification)
    
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
    unique_systems = ErrorType.objects.values_list('system_name', flat=True).distinct()
    unique_system_classifications = ErrorType.objects.values_list('system_classification', flat=True).distinct()
    unique_services = ErrorType.objects.values_list('service_name', flat=True).distinct()
    unique_service_classifications = ErrorType.objects.values_list('service_classification', flat=True).distinct()

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
    event = get_object_or_404(ErrorEvent, id=event_id)
    related_events = ErrorEvent.objects.filter(error_type=event.error_type).exclude(id=event_id).order_by('-timestamp')[:5]
    
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
                error_type = ErrorType.objects.filter(error_code=request.POST.get('error_code')).first()

                if error_type:
                    pass
                else:
                    # Créer un nouveau TYpe
                    error_type = ErrorType.objects.create(
                        system=system,
                        service=service,
                        error_code=request.POST.get('error_code'),
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
                    environment=request.POST.get('environment', 'production')
                )

                # 6. Gestion du ticket d'erreur
                # Vérifier si un ticket avec le même numéro d'erreur existe
                error_ticket = ErrorTicket.objects.filter(error_type__error_code=error_type.error_code).first()

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
                        title=f"Error Event {error_event.id}",
                        description=error_type.error_description,
                        root_cause= request.POST.get('root_cause', ''),
                        assigned_to=request.user.username
                    )

                messages.success(request, f"Événement d'erreur créé avec succès: {error_event.id}")
                return redirect('error_management_systems:event_detail', event_id=error_event.id)

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

@require_http_methods(["GET"])
def check_error_type_exists(request):
    """API pour vérifier si un type d'erreur existe déjà"""
    system_name = request.GET.get('system_name')
    service_name = request.GET.get('service_name')
    error_reason = request.GET.get('error_reason')
    
    if not all([system_name, service_name, error_reason]):
        return JsonResponse({
            'success': False,
            'message': 'Paramètres incomplets'
        }, status=400)
    
    try:
        error_type = ErrorType.objects.get(
            system_name=system_name,
            service_name=service_name,
            error_reason=error_reason
        )
        # Vérifier si un ticket existe
        try:
            ticket = error_type.ticket
            has_ticket = True
            ticket_data = {
                'id': str(ticket.id),
                'reference': ticket.ticket_reference,
                'status': ticket.get_status_display(),
                'priority': ticket.get_priority_display()
            }
        except ErrorTicket.DoesNotExist:
            has_ticket = False
            ticket_data = None
        
        return JsonResponse({
            'success': True,
            'exists': True,
            'error_type': {
                'id': error_type.id,
                'system_name': error_type.system_name,
                'service_name': error_type.service_name,
                'error_reason': error_type.error_reason,
            },
            'has_ticket': has_ticket,
            'ticket': ticket_data
        })
    except ErrorType.DoesNotExist:
        return JsonResponse({
            'success': True,
            'exists': False
        })

@require_POST
def create_error_type_ajax(request):
    """API pour créer un nouveau type d'erreur via AJAX"""
    try:
        data = json.loads(request.body)
        
        # Vérifier les champs obligatoires
        required_fields = ['system_name', 'service_name', 'service_type', 'error_reason']
        for field in required_fields:
            if not data.get(field):
                return JsonResponse({
                    'success': False,
                    'message': f'Le champ {field} est obligatoire'
                }, status=400)
        
        # Vérifier si le type d'erreur existe déjà
        try:
            error_type = ErrorType.objects.get(
                system_name=data['system_name'],
                service_name=data['service_name'],
                error_reason=data['error_reason']
            )
            # Le type d'erreur existe déjà
            return JsonResponse({
                'success': True,
                'exists': True,
                'error_type': {
                    'id': error_type.id,
                    'system_name': error_type.system_name,
                    'service_name': error_type.service_name,
                    'error_reason': error_type.error_reason
                }
            })
        except ErrorType.DoesNotExist:
            # Créer un nouveau type d'erreur
            error_type = ErrorType.objects.create(
                system_name=data['system_name'],
                service_name=data['service_name'],
                service_type=data['service_type'],
                error_reason=data['error_reason'],
                code_erreur=data.get('code_erreur', ''),
                fichiers_impactes=data.get('fichiers_impactes', ''),
                logs=data.get('logs', ''),
                description_technique=data.get('description_technique', ''),
                comportement_attendu=data.get('comportement_attendu', ''),
                procedures_contournement=data.get('procedures_contournement', ''),
                environnement=data.get('environnement', ''),
                niveau_severite=data.get('niveau_severite')
            )
            
            return JsonResponse({
                'success': True,
                'exists': False,
                'created': True,
                'error_type': {
                    'id': error_type.id,
                    'system_name': error_type.system_name,
                    'service_name': error_type.service_name,
                    'error_reason': error_type.error_reason
                }
            })
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'message': 'Format JSON invalide'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Erreur: {str(e)}'
        }, status=500)

@require_POST
def create_ticket_ajax(request):
    """API pour créer un nouveau ticket d'erreur via AJAX"""
    try:
        data = json.loads(request.body)
        
        # Vérifier les champs obligatoires
        if not data.get('error_type_id'):
            return JsonResponse({
                'success': False,
                'message': 'ID du type d\'erreur obligatoire'
            }, status=400)
        
        # Récupérer le type d'erreur
        try:
            error_type = ErrorType.objects.get(id=data['error_type_id'])
        except ErrorType.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': 'Type d\'erreur non trouvé'
            }, status=404)
        
        # Vérifier si un ticket existe déjà pour ce type d'erreur
        try:
            existing_ticket = error_type.ticket
            return JsonResponse({
                'success': False,
                'exists': True,
                'message': 'Un ticket existe déjà pour ce type d\'erreur',
                'ticket': {
                    'id': str(existing_ticket.id),
                    'reference': existing_ticket.ticket_reference,
                    'status': existing_ticket.get_status_display(),
                    'priority': existing_ticket.get_priority_display()
                }
            })
        except ErrorTicket.DoesNotExist:
            # Créer un nouveau ticket
            ticket = ErrorTicket(
                error_type=error_type,
                priority=data.get('priority', 'P3'),
                status=data.get('status', 'OPEN'),
                niveau_criticite=data.get('niveau_criticite', 3),
                symptomes=data.get('symptomes', ''),
                impact=data.get('impact', ''),
                services_affectes=data.get('services_affectes', ''),
                nombre_utilisateurs=data.get('nombre_utilisateurs'),
                charge_systeme=data.get('charge_systeme'),
                responsable=data.get('responsable', ''),
                equipe=data.get('equipe', ''),
                commentaires=data.get('commentaires', '')
            )
            ticket.save()
            
            # Initialiser l'historique
            ticket.historique = {
                'creation': {
                    'timestamp': timezone.now().isoformat(),
                    'status': ticket.status,
                    'priority': ticket.priority
                },
                'changes': []
            }
            ticket.save()
            
            return JsonResponse({
                'success': True,
                'created': True,
                'ticket': {
                    'id': str(ticket.id),
                    'reference': ticket.ticket_reference,
                    'status': ticket.get_status_display(),
                    'priority': ticket.get_priority_display()
                }
            })
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'message': 'Format JSON invalide'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Erreur: {str(e)}'
        }, status=500)
    

from rest_framework import status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from django.contrib.auth import authenticate
from .models import ErrorEvent, ErrorType, ErrorTicket
from .serializers import ErrorEventSerializer
from rest_framework.throttling import UserRateThrottle

class CustomUserRateThrottle(UserRateThrottle):
    rate = '100/minute'  # Adjust as needed

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
    """API endpoint to create a new error event."""
    throttle_classes = [CustomUserRateThrottle]
    system_name = request.data.get('system_name')
    service_name = request.data.get('service_name')
    service_type = request.data.get('service_type')
    error_reason = request.data.get('error_reason')
    error_count = request.data.get('error_count', 1)
    notes = request.data.get('notes', '')
    logs = request.data.get('logs', '')
    code_erreur = request.data.get('code_erreur', '')
    fichiers_impactes = request.data.get('fichiers_impactes', '')
    system_classification = request.POST.get('system_classification', '')
    service_classification = request.POST.get('service_classification', '')
    impact_level = request.POST.get('impact_level', '')


    if not all([system_name, service_name, service_type, error_reason]):
        return Response({"error": "Missing required fields."}, status=status.HTTP_400_BAD_REQUEST)

    try:
        error_type, created = ErrorType.objects.get_or_create(
            system_name=system_name,
            service_name=service_name,
            error_reason=error_reason,
            defaults={
                'service_type': service_type,
                'code_erreur': code_erreur,
                'fichiers_impactes': fichiers_impactes,
                'system_classification': system_classification,
                'service_classification': service_classification,
                'impact_level': impact_level,
            }
        )

        event = ErrorEvent.objects.create(
            system_name=system_name,
            service_type=service_type,
            service_name=service_name,
            error_reason=error_reason,
            error_type=error_type,
            error_count=error_count,
            inserted_by=request.user.username,
            notes=notes,
            logs=logs,
        )

        if created:
            ErrorTicket.objects.create(error_type=error_type)

        serializer = ErrorEventSerializer(event)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)