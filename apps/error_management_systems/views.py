from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.contrib import messages
from django.db.models import Count, Sum
from django.utils import timezone
from django.views.decorators.http import require_POST, require_http_methods
import json

from .models import ErrorType, ErrorEvent, ErrorTicket
from .forms import ErrorTypeForm, ErrorEventForm, ErrorTicketForm

# Page d'accueil
def dashboard1(request):
    """Page d'accueil avec statistiques générales et derniers événements"""
    # Statistiques globales
    stats = {
        'total_error_types': ErrorType.objects.count(),
        'total_error_events': ErrorEvent.objects.count(),
        'open_tickets': ErrorTicket.objects.filter(statut__in=['OPEN', 'IN_PROGRESS']).count(),
        'recent_events': ErrorEvent.objects.order_by('-timestamp')[:5],
        'top_errors': ErrorType.objects.annotate(event_count=Count('events')).order_by('-event_count')[:5],
        'critical_tickets': ErrorTicket.objects.filter(priorite='P1', statut__in=['OPEN', 'IN_PROGRESS']).order_by('date_creation')[:5]
    }
    
    return render(request, 'error_management_systems/home.html', {'stats': stats})

from django.shortcuts import render
from django.db.models import Count, Avg
from .models import ErrorType, ErrorEvent, ErrorTicket
from django.utils import timezone
from django.db import models

def dashboard2(request):
    """Page d'accueil avec statistiques générales et derniers événements"""

    # Statistiques globales
    stats = {
        'total_error_types': ErrorType.objects.count(),
        'total_error_events': ErrorEvent.objects.count(),
        'open_tickets': ErrorTicket.objects.filter(statut__in=['OPEN', 'IN_PROGRESS']).count(),
        'resolved_tickets': ErrorTicket.objects.filter(statut__in=['RESOLVED', 'CLOSED']).count(),
        'recent_events': ErrorEvent.objects.order_by('-timestamp')[:5],
        'top_errors': ErrorType.objects.annotate(event_count=Count('events')).order_by('-event_count')[:5],
        'critical_tickets': ErrorTicket.objects.filter(priorite='P1', statut__in=['OPEN', 'IN_PROGRESS']).order_by('date_creation')[:5],
    }

    # Average Resolution Time
    resolved_tickets = ErrorTicket.objects.filter(statut__in=['RESOLVED', 'CLOSED'], date_resolution__isnull=False)
    if resolved_tickets.exists():
        average_resolution_time = resolved_tickets.annotate(duration=models.ExpressionWrapper(
            models.F('date_resolution') - models.F('date_creation'),
            output_field=models.DurationField()
        )).aggregate(avg_duration=Avg('duration'))['avg_duration']

        if average_resolution_time:
            stats['average_resolution_time'] = round(average_resolution_time.total_seconds() / 3600, 1) # Hours
        else:
            stats['average_resolution_time'] = "N/A"
    else:
        stats['average_resolution_time'] = "N/A"

    # Error Event Trend (Last 7 Days)
    today = timezone.now().date()
    last_7_days = [today - timezone.timedelta(days=i) for i in range(7)]
    event_trend = []
    for day in last_7_days:
        count = ErrorEvent.objects.filter(timestamp__date=day).count()
        event_trend.append({'date': day.strftime('%Y-%m-%d'), 'count': count})
    stats['event_trend'] = reversed(event_trend) # reverse to display from oldest to newest

    # Error Type Distribution (by System Name)
    error_type_distribution = ErrorType.objects.values('system_name').annotate(count=Count('id')).order_by('-count')
    stats['error_type_distribution'] = error_type_distribution

    # Priority Breakdown
    priority_breakdown = ErrorTicket.objects.values('priorite').annotate(count=Count('id')).order_by('-count')
    stats['priority_breakdown'] = priority_breakdown

    # Ticket Status Breakdown
    status_breakdown = ErrorTicket.objects.values('statut').annotate(count=Count('id')).order_by('-count')
    stats['status_breakdown'] = status_breakdown

    # Severity Distribution of Error Types.
    severity_distribution = ErrorType.objects.values('niveau_severite').annotate(count=Count('id')).order_by('-count')
    stats['severity_distribution'] = severity_distribution

    return render(request, 'error_management_systems/home1.html', {'stats': stats})

# ---- ErrorEvent Views ----

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

def create_event(request):
    """Création d'un nouvel événement d'erreur"""
    if request.method == 'POST':
        system_name = request.POST.get('system_name')
        service_name = request.POST.get('service_name')
        service_type = request.POST.get('service_type')
        error_reason = request.POST.get('error_reason')

        # Vérifier si le ErrorType existe
        error_type, created = ErrorType.objects.get_or_create(
            system_name=system_name,
            service_name=service_name,
            error_reason=error_reason,
            defaults={
                'service_type': service_type,
                'code_erreur': request.POST.get('code_erreur', ''),
                'fichiers_impactes': request.POST.get('fichiers_impactes', ''),
                'logs': request.POST.get('logs', '')
            }
        )

        # Créer l'événement d'erreur en associant l'error_type
        event = ErrorEvent(
            system_name=system_name,
            service_type=service_type,
            service_name=service_name,
            error_reason=error_reason,
            error_type=error_type,  # Ajout de l'association
            error_count=request.POST.get('error_count', 1),
            inserted_by=request.POST.get('inserted_by'),
            notes=request.POST.get('notes', '')
        )
        event.save()

        # Si un nouvel ErrorType a été créé, créer aussi un ticket
        if created:
            ErrorTicket.objects.create(error_type=error_type)
            messages.success(request, f"Événement d'erreur créé avec succès, nouveau type d'erreur et ticket créés: {event.id}")
        else:
            messages.success(request, f"Événement d'erreur créé avec succès: {event.id}")

        return redirect('error_management_systems:event_detail', event_id=event.id)

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