from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.contrib import messages
from django.db.models import Count, Sum, Q
from django.utils import timezone
from django.views.decorators.http import require_POST, require_http_methods
import json
from django.contrib.auth.decorators import login_required
from .models import ErrorType, ErrorEvent, ErrorTicket
from .forms import ErrorTypeForm, ErrorEventForm, ErrorTicketForm
from django.db.models.functions import TruncDate

# Page d'accueil
@login_required(login_url='/authentication/login/')
def dashboard1(request):
    """View to render error events time series chart with dynamic filtering."""

    # Additional System Insights
    most_error_prone_system = ErrorEvent.objects.values('system_name').annotate(count=Count('id')).order_by('-count').first()
    most_error_prone_service = ErrorEvent.objects.values('service_name').annotate(count=Count('id')).order_by('-count').first()

    most_common_errors = ErrorType.objects.values('error_reason').annotate(count=Count('id')).order_by('-count')[:5]

    most_impactful_systems = (
        ErrorType.objects.filter(impact_level__in=['critical', 'high'])
        .values('system_name')
        .annotate(count=Count('id'))
        .order_by('-count')[:5]
    )

    top_impacted_components = (
        ErrorType.objects.exclude(source_component="")
        .values('source_component')
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
        'most_common_errors': most_common_errors,
        'most_impactful_systems': most_impactful_systems,
        'top_impacted_components': top_impacted_components,

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

    return render(request, 'error_management_systems/dashboard1.html', {'context': context})

@login_required(login_url='/authentication/login/')
def dashboard2(request):
    """
    View for the professional dashboard, providing an overview of Error Types,
    Error Events, and Error Tickets.
    """

    # Error Type Overview (Widget 1)
    total_error_types = ErrorType.objects.count()
    error_type_categories = ErrorType.objects.values('error_category').annotate(count=Count('error_category'))
    error_type_impact_levels = ErrorType.objects.values('impact_level').annotate(count=Count('impact_level'))
    expected_vs_unexpected = ErrorType.objects.values('type_error').annotate(count=Count('type_error'))

    # Error Type List (Widget 2)
    error_types = ErrorType.objects.order_by('-created_at')[:10]

    # Error Event Overview (Widget 3)
    total_error_events = ErrorEvent.objects.count()
    error_events_time_series = (ErrorEvent.objects.annotate(date=TruncDate('timestamp')).values('date').annotate(count=Count('id')).order_by('date'))
    
    top_systems_events = ErrorEvent.objects.values('system_name').annotate(count=Count('id')).order_by('-count')[:5]
    top_services_events = ErrorEvent.objects.values('service_name').annotate(count=Count('id')).order_by('-count')[:5]

    # Additional System Insights
    most_error_prone_system = ErrorEvent.objects.values('system_name').annotate(count=Count('id')).order_by('-count').first()
    most_error_prone_service = ErrorEvent.objects.values('service_name').annotate(count=Count('id')).order_by('-count').first()

    most_common_errors = ErrorType.objects.values('error_reason').annotate(count=Count('id')).order_by('-count')[:5]

    most_impactful_systems = (
        ErrorType.objects.filter(impact_level__in=['critical', 'high'])
        .values('system_name')
        .annotate(count=Count('id'))
        .order_by('-count')[:5]
    )

    top_impacted_components = (
        ErrorType.objects.exclude(source_component="")
        .values('source_component')
        .annotate(count=Count('id'))
        .order_by('-count')[:5]
    )

    # Error Event List (Widget 4)
    error_events = ErrorEvent.objects.order_by('-timestamp')[:10]

    # Error Ticket Overview (Widget 5)
    total_error_tickets = ErrorTicket.objects.count()
    error_ticket_statuses = ErrorTicket.objects.values('statut').annotate(count=Count('statut'))
    error_ticket_priorities = ErrorTicket.objects.values('priorite').annotate(count=Count('priorite'))
    
    # Calculate average ticket resolution time
    resolved_tickets = ErrorTicket.objects.filter(statut='RESOLVED', date_resolution__isnull=False)
    if resolved_tickets.exists():
        total_duration = sum([(ticket.date_resolution - ticket.date_creation).total_seconds() for ticket in resolved_tickets])
        average_resolution_time = total_duration / resolved_tickets.count() / 3600  # in hours
    else:
        average_resolution_time = 0

    # Error Ticket List (Widget 8)
    error_tickets = ErrorTicket.objects.order_by('-date_creation')[:10]

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
        # New Insights
        'most_error_prone_system': most_error_prone_system,
        'most_error_prone_service': most_error_prone_service,
        'most_common_errors': most_common_errors,
        'most_impactful_systems': most_impactful_systems,
        'top_impacted_components': top_impacted_components,
    }

    return render(request, 'error_management_systems/dashboard2.html', context)


# ---- ErrorEvent Views ----
@login_required(login_url='/authentication/login/')
def event_list(request):
    """Liste des événements d'erreur avec filtres"""
    events = ErrorEvent.objects.all().order_by('-timestamp')
    
    # Filtres
    system_filter = request.GET.get('system')
    service_filter = request.GET.get('service')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    
    if system_filter:
        events = events.filter(system_name__icontains=system_filter)
    if service_filter:
        events = events.filter(service_name__icontains=service_filter)
    if date_from:
        events = events.filter(timestamp__gte=date_from)
    if date_to:
        events = events.filter(timestamp__lte=date_to)
    
    # Liste des systèmes et services pour les filtres
    systems = ErrorType.objects.values_list('system_name', flat=True).distinct()
    services = ErrorType.objects.values_list('service_name', flat=True).distinct()
    
    context = {
        'events': events,
        'systems': systems,
        'services': services,
    }
    
    return render(request, 'error_management_systems/event_list.html', context)

@login_required(login_url='/authentication/login/')
def event_detail(request, event_id):
    """Détail d'un événement d'erreur"""
    event = get_object_or_404(ErrorEvent, id=event_id)
    related_events = ErrorEvent.objects.filter(error_type=event.error_type).exclude(id=event_id).order_by('-timestamp')[:5]
    
    # Vérifier si un ticket existe pour ce type d'erreur
    try:
        ticket = event.error_type.ticket
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

from django.db import transaction

@login_required(login_url='/authentication/login/')
def create_event(request):
    """Création d'un nouvel événement d'erreur"""
    if request.method == 'POST':
        system_name = request.POST.get('system_name')
        service_name = request.POST.get('service_name')
        service_type = request.POST.get('service_type')
        system_classification = request.POST.get('system_classification', '')
        service_classification = request.POST.get('service_classification', '')
        error_reason = request.POST.get('error_reason')

        try:
            with transaction.atomic():
                # Step 1: Create or get ErrorType
                error_type, created = ErrorType.objects.get_or_create(
                    system_name=system_name,
                    service_name=service_name,
                    error_reason=error_reason,
                    defaults={
                        'service_type': service_type,
                        'code_erreur': request.POST.get('code_erreur', ''),
                        'fichiers_impactes': request.POST.get('fichiers_impactes', ''),
                        'system_classification': system_classification,
                        'service_classification': service_classification,
                    }
                )

                # Step 2: Create ErrorEvent
                event = ErrorEvent(
                    system_name=system_name,
                    service_type=service_type,
                    service_name=service_name,
                    error_reason=error_reason,
                    error_type=error_type,
                    error_count=request.POST.get('error_count', 1),
                    inserted_by=request.user.username,
                    notes=request.POST.get('notes', ''),
                    logs=request.POST.get('logs', '')
                )
                event.save()

                # Step 3: Create or update ErrorTicket
                ticket, ticket_created = ErrorTicket.objects.get_or_create(
                    error_type=error_type,
                    defaults={'statut': 'OPEN'}
                )
                if not ticket_created:
                    ticket.statut = 'OPEN'
                    ticket.save()

                messages.success(request, f"Événement d'erreur créé avec succès et ticket ouvert: {event.id}")
                return redirect('error_management_systems:event_detail', event_id=event.id)

        except Exception as e:
            messages.error(request, f"Une erreur est survenue lors de la création de l'événement: {e}")
            # Log the exception for debugging
            import logging
            logging.exception("Error during create_event")
            return redirect('error_management_systems:create_event') #or render with form errors.

    # Pour le formulaire GET initial
    error_types = ErrorType.objects.all().order_by('system_name', 'service_name')
    systems = ErrorType.objects.values_list('system_name', flat=True).distinct()
    services = ErrorType.objects.values_list('service_name', flat=True).distinct()

    context = {
        'error_types': error_types,
        'systems': systems,
        'services': services,
        'form': ErrorEventForm()
    }

    return render(request, 'error_management_systems/create_event.html', context)


@login_required(login_url='/authentication/login/')
def modify_error_type_details(request, event_id, error_type_id):
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
    """Liste des types d'erreurs avec filtres et statistiques"""
    error_types = ErrorType.objects.annotate(event_count=Count('events')).order_by('-event_count')
    
    # Filtres
    system_filter = request.GET.get('system')
    service_filter = request.GET.get('service')
    
    if system_filter:
        error_types = error_types.filter(system_name__icontains=system_filter)
    if service_filter:
        error_types = error_types.filter(service_name__icontains=service_filter)
    
    # Liste des systèmes et services pour les filtres
    systems = ErrorType.objects.values_list('system_name', flat=True).distinct()
    services = ErrorType.objects.values_list('service_name', flat=True).distinct()
    
    context = {
        'error_types': error_types,
        'systems': systems,
        'services': services,
    }
    
    return render(request, 'error_management_systems/error_type_list.html', context)

@login_required(login_url='/authentication/login/')
def error_type_detail(request, error_type_id):
    """Détail d'un type d'erreur avec ses événements associés"""
    error_type = get_object_or_404(ErrorType, id=error_type_id)
    events = error_type.events.all().order_by('-timestamp')
    
    # Vérifier si un ticket existe
    try:
        ticket = error_type.ticket
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
    """Liste des tickets avec filtres"""
    tickets = ErrorTicket.objects.all().order_by('-date_creation')
    
    # Filtres
    status_filter = request.GET.get('status')
    priority_filter = request.GET.get('priority')
    system_filter = request.GET.get('system')
    
    if status_filter:
        tickets = tickets.filter(statut=status_filter)
    if priority_filter:
        tickets = tickets.filter(priorite=priority_filter)
    if system_filter:
        tickets = tickets.filter(error_type__system_name__icontains=system_filter)
    
    # Données pour les filtres
    systems = ErrorType.objects.values_list('system_name', flat=True).distinct()
    
    context = {
        'tickets': tickets,
        'systems': systems,
        'status_choices': ErrorTicket.STATUS_CHOICES,
        'priority_choices': ErrorTicket.PRIORITY_CHOICES
    }
    
    return render(request, 'error_management_systems/ticket_list.html', context)

@login_required(login_url='/authentication/login/')
def ticket_detail(request, ticket_id):
    """Détail d'un ticket"""
    ticket = get_object_or_404(ErrorTicket, id=ticket_id)
    events = ticket.error_type.events.all().order_by('-timestamp')
    
    context = {
        'ticket': ticket,
        'error_type': ticket.error_type,
        'events': events,
        'event_count': events.count(),
        'total_errors': events.aggregate(Sum('error_count'))['error_count__sum'] or 0,
        'ticket_duration': ticket.get_duration()
    }
    
    return render(request, 'error_management_systems/ticket_detail.html', context)

@login_required(login_url='/authentication/login/')
def edit_ticket(request, ticket_id):
    """Édition d'un ticket"""
    ticket = get_object_or_404(ErrorTicket, id=ticket_id)
    
    if request.method == 'POST':
        form = ErrorTicketForm(request.POST, instance=ticket)
        if form.is_valid():
            # Capturer l'état précédent pour l'historique
            old_status = ticket.statut
            old_priority = ticket.priorite
            
            # Sauvegarder les modifications
            updated_ticket = form.save(commit=False)
            
            # Mettre à jour l'historique
            if not updated_ticket.historique:
                updated_ticket.historique = {}
            
            # Enregistrer les changements d'état et de priorité dans l'historique
            if old_status != updated_ticket.statut or old_priority != updated_ticket.priorite:
                timestamp = timezone.now().isoformat()
                if 'changes' not in updated_ticket.historique:
                    updated_ticket.historique['changes'] = []
                
                updated_ticket.historique['changes'].append({
                    'timestamp': timestamp,
                    'status_change': {
                        'from': old_status,
                        'to': updated_ticket.statut
                    } if old_status != updated_ticket.statut else None,
                    'priority_change': {
                        'from': old_priority,
                        'to': updated_ticket.priorite
                    } if old_priority != updated_ticket.priorite else None
                })
            
            updated_ticket.save()
            messages.success(request, f"Ticket mis à jour: {ticket.ticket_reference}")
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
                'statut': ticket.get_statut_display(),
                'priorite': ticket.get_priorite_display()
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
                    'statut': existing_ticket.get_statut_display(),
                    'priorite': existing_ticket.get_priorite_display()
                }
            })
        except ErrorTicket.DoesNotExist:
            # Créer un nouveau ticket
            ticket = ErrorTicket(
                error_type=error_type,
                priorite=data.get('priorite', 'P3'),
                statut=data.get('statut', 'OPEN'),
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
                    'statut': ticket.statut,
                    'priorite': ticket.priorite
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
                    'statut': ticket.get_statut_display(),
                    'priorite': ticket.get_priorite_display()
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
    rate = '1000/day'  # Adjust as needed

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