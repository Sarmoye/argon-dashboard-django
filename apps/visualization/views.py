from django.http import HttpResponse
from django.template import loader
from django.contrib.auth.decorators import login_required
from apps.analysis.models import FicheErreur 
from django.shortcuts import render
from django.contrib.auth.decorators import user_passes_test
from django.db.models import Count, Sum

def check_user_role(user, allowed_roles=None):
    """
    Check if user has specified role(s)
    
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




from django.db.models import Count, Avg
from django.db.models.functions import TruncDate
from datetime import datetime, timedelta

def index(request):
    # Récupérer le système sélectionné depuis les paramètres GET
    selected_system = request.GET.get('system', None)
    date_range = request.GET.get('date_range', '7')  # Par défaut 7 jours
    
    # Query de base
    queryset = FicheErreur.objects.all()
    
    # Filtrer par système si sélectionné
    if selected_system:
        queryset = queryset.filter(system_name=selected_system)

    # Calculer la date de début selon la période sélectionnée
    days = int(date_range)
    start_date = datetime.now() - timedelta(days=days)
    queryset = queryset.filter(timestamp__gte=start_date)

    # Statistiques générales
    error_stats = {
        'total_errors': queryset.count(),
        'open_errors': queryset.filter(statut='Ouvert').count(),
        'avg_resolution_time': queryset.exclude(delai_resolution__isnull=True).aggregate(Avg('delai_resolution'))['delai_resolution__avg'],
        'critical_errors': queryset.filter(gravite='Haute').count(),
    }

    # Données pour les graphiques
    errors_by_day = queryset.annotate(
        date=TruncDate('timestamp')
    ).values('date').annotate(
        count=Count('id')
    ).order_by('date')

    errors_by_system = queryset.values('system_name').annotate(
        count=Count('id')
    ).order_by('-count')

    errors_by_priority = queryset.values('priorite').annotate(
        count=Count('id')
    ).order_by('priorite')

    errors_by_status = queryset.values('statut').annotate(
        count=Count('id')
    ).order_by('statut')

    # Liste des systèmes pour le filtre
    systems = FicheErreur.objects.values_list('system_name', flat=True).distinct()

    context = {
        'error_stats': error_stats,
        'errors_by_day': list(errors_by_day),
        'errors_by_system': list(errors_by_system),
        'errors_by_priority': list(errors_by_priority),
        'errors_by_status': list(errors_by_status),
        'systems': systems,
        'selected_system': selected_system,
        'date_range': date_range,
    }
    
    return render(request, 'visualization/visualization_home.html', context)

