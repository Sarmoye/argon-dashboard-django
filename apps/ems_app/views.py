# errors/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from .models import ErrorEvent, ErrorType, ErrorTicket
from django.http import HttpResponseRedirect
from django.urls import reverse
from .forms import ErrorTypeForm, ErrorEventForm, ErrorTicketForm  # Nous allons créer ces formulaires

def report_error(request):
    """Vue pour la première étape: création du type d'erreur"""
    if request.method == 'POST':
        form = ErrorTypeForm(request.POST)
        if form.is_valid():
            error_type = form.save()
            
            # Stocker l'ID du type d'erreur en session pour les étapes suivantes
            request.session['error_type_id'] = str(error_type.id)
            
            # Rediriger vers la deuxième étape
            return redirect('ems_app:report_error_details')
    else:
        form = ErrorTypeForm()
    
    return render(request, 'errors/report_error.html', {'form': form})

def report_error_details(request):
    """Vue pour la deuxième étape: détails de l'événement d'erreur"""
    # Vérifier que la première étape a été complétée
    error_type_id = request.session.get('error_type_id')
    if not error_type_id:
        messages.error(request, "Veuillez d'abord définir le type d'erreur")
        return redirect('ems_app:report_error')
    
    error_type = get_object_or_404(ErrorType, id=error_type_id)
    
    if request.method == 'POST':
        form = ErrorEventForm(request.POST)
        if form.is_valid():
            error_event = form.save(commit=False)
            error_event.error_type = error_type
            error_event.save()
            
            # Stocker l'ID de l'événement d'erreur pour l'étape suivante
            request.session['error_event_id'] = str(error_event.id)
            
            # Rediriger vers la troisième étape
            return redirect('ems_app:create_error_ticket')
    else:
        form = ErrorEventForm(initial={'inserted_by': request.user.username if request.user.is_authenticated else ''})
    
    return render(request, 'errors/report_error_details.html', {'form': form, 'error_type': error_type})

def create_error_ticket(request):
    """Vue pour la troisième étape: création du ticket d'erreur"""
    # Vérifier que les étapes précédentes ont été complétées
    error_type_id = request.session.get('error_type_id')
    error_event_id = request.session.get('error_event_id')
    
    if not error_type_id or not error_event_id:
        messages.error(request, "Veuillez suivre le processus de signalement depuis le début")
        return redirect('ems_app:report_error')
    
    error_type = get_object_or_404(ErrorType, id=error_type_id)
    error_event = get_object_or_404(ErrorEvent, id=error_event_id)
    
    # Vérifier si un ticket existe déjà pour ce type d'erreur
    try:
        ticket = ErrorTicket.objects.get(error_type=error_type)
        messages.info(request, "Un ticket existe déjà pour ce type d'erreur")
        
        # Nettoyer la session et rediriger vers le détail de l'événement
        del request.session['error_type_id']
        del request.session['error_event_id']
        return redirect('ems_app:error_detail', reference_id=error_event.reference_id)
    except ErrorTicket.DoesNotExist:
        # Créer un nouveau ticket si nécessaire
        if request.method == 'POST':
            form = ErrorTicketForm(request.POST)
            if form.is_valid():
                ticket = form.save(commit=False)
                ticket.error_type = error_type
                ticket.save()
                
                # Nettoyer la session et rediriger vers la page de détails
                del request.session['error_type_id']
                del request.session['error_event_id']
                
                messages.success(request, f"Erreur enregistrée avec succès: {error_event.reference_id}")
                return redirect('ems_app:error_detail', reference_id=error_event.reference_id)
        else:
            # Préremplir avec les informations disponibles
            initial_data = {
                'symptomes': f"Premier signalement: {error_type.error_reason}",
                'impact': "À déterminer",
                'services_affectes': error_type.service_name
            }
            form = ErrorTicketForm(initial=initial_data)
    
    return render(request, 'errors/create_error_ticket.html', {'form': form, 'error_type': error_type})

def error_detail(request, reference_id):
    """Vue pour afficher les détails d'une erreur spécifique"""
    try:
        event = ErrorEvent.objects.get(reference_id=reference_id)
        return render(request, 'errors/error_detail.html', {'event': event})
    except ErrorEvent.DoesNotExist:
        messages.error(request, f"Erreur avec référence {reference_id} non trouvée")
        return redirect('ems_app:error_list')

def edit_error_details(request, reference_id):
    """Vue pour modifier les détails d'une erreur"""
    event = get_object_or_404(ErrorEvent, reference_id=reference_id)
    error_type = event.error_type
    
    if request.method == 'POST':
        error_type_form = ErrorTypeForm(request.POST, instance=error_type, prefix='type')
        event_form = ErrorEventForm(request.POST, instance=event, prefix='event')
        
        if error_type_form.is_valid() and event_form.is_valid():
            error_type_form.save()
            event_form.save()
            messages.success(request, f"Les détails de l'erreur {reference_id} ont été mis à jour")
            return redirect('ems_app:error_detail', reference_id=reference_id)
    else:
        error_type_form = ErrorTypeForm(instance=error_type, prefix='type')
        event_form = ErrorEventForm(instance=event, prefix='event')
    
    return render(request, 'errors/edit_error_details.html', {
        'error_type_form': error_type_form,
        'event_form': event_form,
        'event': event
    })
    
# errors/views.py
# Ajoutez ces imports en haut du fichier
from django.db.models import Count, Avg, F, ExpressionWrapper, fields, Q
from django.utils import timezone
from datetime import timedelta
import json
from django.db.models.functions import Cast, Extract

def dashboard(request):
    """Vue pour le tableau de bord de suivi des erreurs"""
    # Calculer la date il y a 30 jours
    thirty_days_ago = timezone.now() - timedelta(days=30)
    
    # Statistiques générales
    stats = {
        'total_errors': ErrorEvent.objects.count(),
        'active_errors': ErrorEvent.objects.filter(error_type__ticket__statut__in=['OPEN', 'IN_PROGRESS', 'PENDING']).count(),
        'resolved_errors': ErrorEvent.objects.filter(error_type__ticket__statut='RESOLVED').count(),
        'error_types': ErrorType.objects.count(),
        'recent_errors': ErrorEvent.objects.filter(timestamp__gte=thirty_days_ago).count(),
        'avg_resolution_time': ErrorTicket.objects.filter(
            statut='RESOLVED',
            date_resolution__isnull=False
        ).annotate(
            resolution_hours=ExpressionWrapper(
                F('date_resolution') - F('date_creation'), 
                output_field=fields.DurationField()
            )
        ).aggregate(
            avg_hours=Avg(
                ExpressionWrapper(
                    F('resolution_hours') / 3600.0,  # Convertit en heures
                    output_field=fields.FloatField()
                )
            )
        )['avg_hours'] or 0
    }
    
    # Données pour le graphique des erreurs par système
    system_errors = list(ErrorType.objects.values('system_name')
                        .annotate(count=Count('events'))
                        .order_by('-count')[:10])
    
    # Données pour le graphique des tendances temporelles
    # Agréger par jour les 30 derniers jours
    daily_errors = ErrorEvent.objects.filter(
        timestamp__gte=thirty_days_ago
    ).extra({
        'date': "date(timestamp)"
    }).values('date').annotate(
        count=Count('id')
    ).order_by('date')
    
    # Données pour la distribution des priorités
    priority_distribution = list(ErrorTicket.objects.values('priorite')
                               .annotate(count=Count('id'))
                               .order_by('priorite'))
    
    # Temps moyen de résolution par priorité
    resolution_by_priority = list(ErrorTicket.objects.filter(
        statut='RESOLVED',
        date_resolution__isnull=False
    ).values('priorite').annotate(
        avg_hours=Avg(
            ExpressionWrapper(
                Extract('date_resolution', 'epoch') - Extract('date_creation', 'epoch'),
                output_field=fields.FloatField()
            ) / 3600.0
        )
    ).order_by('priorite'))
    
    # Top 5 des erreurs les plus fréquentes
    top_errors = list(ErrorType.objects.annotate(
        events_count=Count('events')
    ).values('system_name', 'error_reason', 'events_count')
    .order_by('-events_count')[:5])
    
    # Préparer les données pour les graphiques
    chart_data = {
        'system_labels': json.dumps([item['system_name'] for item in system_errors]),
        'system_counts': json.dumps([item['count'] for item in system_errors]),
        
        'daily_dates': json.dumps([str(item['date']) for item in daily_errors]),
        'daily_counts': json.dumps([item['count'] for item in daily_errors]),
        
        'priority_labels': json.dumps([dict(ErrorTicket.PRIORITY_CHOICES)[item['priorite']] for item in priority_distribution]),
        'priority_counts': json.dumps([item['count'] for item in priority_distribution]),
        
        'resolution_priority_labels': json.dumps([dict(ErrorTicket.PRIORITY_CHOICES)[item['priorite']] for item in resolution_by_priority]),
        'resolution_priority_times': json.dumps([round(item['avg_hours'], 1) for item in resolution_by_priority]),
    }
    
    # Liste des erreurs récentes non résolues
    recent_unresolved = ErrorEvent.objects.filter(
        error_type__ticket__statut__in=['OPEN', 'IN_PROGRESS']
    ).order_by('-timestamp')[:10]
    
    context = {
        'stats': stats,
        'chart_data': chart_data,
        'top_errors': top_errors,
        'recent_unresolved': recent_unresolved,
    }
    
    return render(request, 'errors/dashboard.html', context)