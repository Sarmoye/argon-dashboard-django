from django.http import HttpResponse
from django.template import loader
from django.contrib.auth.decorators import login_required
from apps.sources_data_app.models import SourceData 
from apps.analysis.models import FicheErreur 
from django.shortcuts import render
from django.contrib.auth.decorators import user_passes_test

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


from django.db.models import Count, Sum
from django.shortcuts import render

from django.shortcuts import render
from django.db.models import Count, Avg, F, Q
from django.db.models.functions import TruncDay

def index(request):
    # Trier les données par timestamp en ordre décroissant
    source_data = SourceData.objects.filter(validation_status='Validated').order_by('-timestamp')
    
    # Filtrer pour éviter les doublons sur les clés spécifiques
    total_errors = FicheErreur.objects.values(
        "system_name", "service_type", "service_name", "error_reason"
    ).distinct()
    
    # On considère comme "ouvertes" les fiches avec statut "Ouvert" ou resolution "Non commencé"
    open_errors = FicheErreur.objects.filter(
        Q(statut="Ouvert") | Q(statut_resolution="Non commencé")
    ).count()
    
    resolved_errors = total_errors - open_errors

    # Moyenne du délai de résolution (le champ delai_resolution est de type DurationField)
    avg_resolution = FicheErreur.objects.aggregate(avg_delai=Avg('delai_resolution'))['avg_delai']
    
    # Score moyen de criticité basé sur le champ niveau_criticite
    avg_criticite = FicheErreur.objects.aggregate(avg=Avg('niveau_criticite'))['avg']
    
    # Graphique d'évolution temporelle
    errors_by_day = (
        FicheErreur.objects
        .annotate(day=TruncDay('timestamp'))
        .values('day')
        .annotate(count=Count('id'))
        .order_by('day')
    )
    # Préparation des données pour Chart.js
    evolution_labels = [error['day'].strftime('%Y-%m-%d') for error in errors_by_day]
    evolution_counts = [error['count'] for error in errors_by_day]
    
    # Histogramme des priorités : ici nous utilisons priorite_numerique (vous pouvez adapter selon vos besoins)
    priority_data = (
        FicheErreur.objects
        .values('priorite_numerique')
        .annotate(count=Count('id'))
        .order_by('priorite_numerique')
    )
    priority_labels = [str(item['priorite_numerique']) for item in priority_data]
    priority_values = [item['count'] for item in priority_data]

    # Alertes et notifications :
    # Exemple : erreurs avec une criticité maximale (niveau 5) et celles dont le temps écoulé dépasse le délai prévu
    critical_errors = FicheErreur.objects.filter(niveau_criticite=5).count()
    errors_with_delay_issue = FicheErreur.objects.filter(
        delai_resolution__isnull=False,
        delai_ecoule__gt=F('delai_resolution')
    ).count()

    context = {
        'total_errors': total_errors,
        'open_errors': open_errors,
        'resolved_errors': resolved_errors,
        'avg_resolution': avg_resolution,
        'avg_criticite': avg_criticite,
        'evolution_labels': evolution_labels,
        'evolution_counts': evolution_counts,
        'priority_labels': priority_labels,
        'priority_values': priority_values,
        'critical_errors': critical_errors,
        'errors_with_delay_issue': errors_with_delay_issue,
    }
    return render(request, 'visualization/visualization_home.html', context)

