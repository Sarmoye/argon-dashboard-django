# errors/views.py
from django.shortcuts import render, redirect
from django.contrib import messages
from django.utils import timezone
from .models import ErrorEvent, ErrorType, ErrorTicket

def report_error(request):
    """Vue pour signaler une nouvelle erreur"""
    if request.method == 'POST':
        # Récupérer les données du formulaire
        system_name = request.POST.get('system_name')
        service_type = request.POST.get('service_type')
        service_name = request.POST.get('service_name')
        error_reason = request.POST.get('error_reason')
        code_erreur = request.POST.get('code_erreur', '')
        error_count = int(request.POST.get('error_count', 1))
        domain = request.POST.get('domain')
        logs = request.POST.get('logs', '')
        version_system = request.POST.get('version_system', '')
        comportement_attendu = request.POST.get('comportement_attendu', '')
        inserted_by = request.POST.get('inserted_by')
        notes = request.POST.get('notes', '')
        correction_automatique = 'correction_automatique' in request.POST
        
        # Chercher ou créer un ErrorType correspondant
        error_type, created = ErrorType.objects.get_or_create(
            system_name=system_name,
            error_reason=error_reason,
            defaults={
                'service_type': service_type,
                'service_name': service_name,
                'code_erreur': code_erreur,
                'comportement_attendu': comportement_attendu,
                'correction_automatique': correction_automatique
            }
        )
        
        # Créer un ErrorEvent
        error_event = ErrorEvent.objects.create(
            error_type=error_type,
            error_count=error_count,
            domain=domain,
            logs=logs,
            version_system=version_system,
            inserted_by=inserted_by,
            notes=notes
        )
        
        # Si on vient de créer un nouveau ErrorType, créer aussi un ErrorTicket associé
        if created:
            ErrorTicket.objects.create(
                error_type=error_type,
                symptomes=f"Premier signalement: {error_reason}",
                impact="À déterminer",
                services_affectes=service_name
            )
            messages.success(request, f"Erreur enregistrée avec un nouveau ticket: {error_event.reference_id}")
        else:
            messages.success(request, f"Erreur enregistrée: {error_event.reference_id}")
        
        return redirect('ems_app:error_list')  # Rediriger vers la liste des erreurs
        
    return render(request, 'errors/report_error.html')

def error_list(request):
    """Vue pour afficher la liste des erreurs récentes"""
    events = ErrorEvent.objects.all().order_by('-timestamp')[:50]
    return render(request, 'errors/error_list.html', {'events': events})

def error_detail(request, reference_id):
    """Vue pour afficher les détails d'une erreur spécifique"""
    try:
        event = ErrorEvent.objects.get(reference_id=reference_id)
        return render(request, 'errors/error_detail.html', {'event': event})
    except ErrorEvent.DoesNotExist:
        messages.error(request, f"Erreur avec référence {reference_id} non trouvée")
        return redirect('ems_app:error_list')
    
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