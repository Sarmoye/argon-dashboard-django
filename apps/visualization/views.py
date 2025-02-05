from django.http import HttpResponse
from django.template import loader
from django.contrib.auth.decorators import login_required
from apps.analysis.models import FicheErreur 
from django.shortcuts import render
from django.contrib.auth.decorators import user_passes_test
from django.db.models import Count, Sum, Avg

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

def index(request):
    # Filtrer pour éviter les doublons sur les clés spécifiques
    distinct_errors = FicheErreur.objects.values("error_reason").distinct()

    # Nombre total d'erreurs distinctes
    total_erreurs_distinctes = distinct_errors.count()
    
    # Répartition par statut (en utilisant le queryset distinct)
    erreurs_ouvertes = distinct_errors.filter(statut="Ouvert").count()
    erreurs_resolues = distinct_errors.filter(statut="Résolu").count()
    
    # Répartition par système (distinct par system_name)
    erreurs_par_systeme = (FicheErreur.objects.values("system_name").annotate(distinct_errors=Count("error_reason", distinct=True)))
    
    # Répartition par gravité (distinct par gravite)
    erreurs_par_gravite = (FicheErreur.objects.values("gravite").annotate(distinct_errors=Count("error_reason", distinct=True)))

    # Répartition par priorité (distinct par priorite)
    erreurs_par_priorite = (FicheErreur.objects.values("priorite").annotate(distinct_errors=Count("error_reason", distinct=True)))

    erreurs_ouvertes_per_system = FicheErreur.objects.filter(statut="Ouvert").values("system_name").annotate(distinct_errors=Count("error_reason", distinct=True))

    # Calcul du temps moyen de résolution pour chaque erreur distincte
    erreurs_moyenne_temps = (FicheErreur.objects.values("error_reason").annotate(moyenne_temps=Avg("delai_resolution")))

    # Calcul de la moyenne globale des moyennes
    moyenne_globale_resolution = erreurs_moyenne_temps.aggregate(Avg("moyenne_temps"))["moyenne_temps__avg"]

    context = {
        'total_erreurs_distinctes': total_erreurs_distinctes,
        'erreurs_ouvertes': erreurs_ouvertes,
        'erreurs_resolues': erreurs_resolues,
        'erreurs_par_systeme': erreurs_par_systeme,
        'erreurs_par_priorite': erreurs_par_priorite,
        'erreurs_par_gravite': erreurs_par_gravite,
        'erreurs_ouvertes_per_system': erreurs_ouvertes_per_system,
        'distinct_errors': distinct_errors,
        'moyenne_globale_resolution':moyenne_globale_resolution,
    }
    return render(request, 'visualization/visualization_home.html', context)

