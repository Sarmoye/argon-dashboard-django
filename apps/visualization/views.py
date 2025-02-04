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
    distinct_errors = FicheErreur.objects.values(
        "system_name", "service_type", "service_name", "error_reason"
    ).distinct()

    # Nombre total d'erreurs distinctes
    total_erreurs_distinctes = distinct_errors.count()
    
    # Répartition par statut (en utilisant le queryset distinct)
    erreurs_ouvertes = distinct_errors.filter(statut="Ouvert").count()
    erreurs_encours = distinct_errors.filter(statut="En cours").count()
    erreurs_resolues = distinct_errors.filter(statut="Résolu").count()
    
    # Répartition par système (distinct par system_name)
    erreurs_par_systeme = distinct_errors.values('system_name').annotate(total=Count('system_name'))
    
    # Répartition par gravité (distinct par gravite)
    erreurs_par_gravite = distinct_errors.values('gravite').annotate(total=Count('gravite'))
    
    # Répartition par service (distinct par service_name)
    erreurs_par_service = distinct_errors.values('service_name').annotate(total=Count('service_name'))
    
    # Impact utilisateur : somme du nombre d'utilisateurs impactés sur toutes les fiches
    # Remarque : comme 'nombre_utilisateurs_impactes' n'est pas dans le queryset distinct, on effectue une agrégation séparée
    impact_utilisateur = FicheErreur.objects.filter(nombre_utilisateurs_impactes__isnull=False)\
                            .aggregate(total=Sum('nombre_utilisateurs_impactes'))['total']
    if impact_utilisateur is None:
        impact_utilisateur = 0

    context = {
        'total_erreurs': total_erreurs_distinctes,
        'erreurs_ouvertes': erreurs_ouvertes,
        'erreurs_encours': erreurs_encours,
        'erreurs_resolues': erreurs_resolues,
        'erreurs_par_systeme': erreurs_par_systeme,
        'erreurs_par_gravite': erreurs_par_gravite,
        'erreurs_par_service': erreurs_par_service,
        'impact_utilisateur': impact_utilisateur,
        'source_data': source_data,
        'distinct_errors': distinct_errors,
    }
    return render(request, 'visualization/visualization_home.html', context)

