# -*- encoding: utf-8 -*-
"""
Copyright (c) 2019 - present AppSeed.us
"""

from django import template
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseRedirect
from django.template import loader
from django.urls import reverse
import logging
from django.template import loader
from django.contrib.auth.decorators import login_required
from apps.analysis.models import FicheErreur 
from apps.sources_data_app.models import SourceData
from django.shortcuts import render
from django.db.models import Count, Sum, Avg
from django.db.models.functions import TruncDate
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

@login_required(login_url='/authentication/login/')
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
    
    # Répartition par gravité (distinct par gravite) pour les erreurs avec statut "Ouvert"
    erreurs_par_gravite = (
        FicheErreur.objects.filter(statut="Ouvert")
        .values("gravite")
        .annotate(distinct_errors=Count("error_reason", distinct=True))
    )

    # Répartition par priorité (distinct par priorite) pour les erreurs avec statut "Ouvert"
    erreurs_par_priorite = (
        FicheErreur.objects.filter(statut="Ouvert")
        .values("priorite")
        .annotate(distinct_errors=Count("error_reason", distinct=True))
    )

    erreurs_ouvertes_per_system = FicheErreur.objects.filter(statut="Ouvert").values("system_name").annotate(distinct_errors=Count("error_reason", distinct=True))

    # Calcul du temps moyen de résolution pour chaque erreur distincte
    erreurs_moyenne_temps = (FicheErreur.objects.values("error_reason").annotate(moyenne_temps=Avg("delai_resolution")))

    # Calcul de la moyenne globale des moyennes
    moyenne_globale_resolution = erreurs_moyenne_temps.aggregate(Avg("moyenne_temps"))["moyenne_temps__avg"]

    # Get error evolution for the last 30 days
    from django.utils import timezone

    start_date = timezone.now() - timedelta(days=30)

    
    error_evolution = (
        FicheErreur.objects
        .filter(timestamp__gte=start_date)
        .annotate(date=TruncDate('timestamp'))
        .values('date')
        .annotate(count=Count('id'))
        .order_by('date')
    )
    

    context = {
        'segment': 'index',
        'total_erreurs_distinctes': total_erreurs_distinctes,
        'erreurs_ouvertes': erreurs_ouvertes,
        'erreurs_resolues': erreurs_resolues,
        'erreurs_par_systeme': erreurs_par_systeme,
        'erreurs_par_priorite': erreurs_par_priorite,
        'erreurs_par_gravite': erreurs_par_gravite,
        'erreurs_ouvertes_per_system': erreurs_ouvertes_per_system,
        'distinct_errors': distinct_errors,
        'moyenne_globale_resolution':moyenne_globale_resolution,
        'error_evolution': error_evolution,
        }

    html_template = loader.get_template('home/index.html')
    return HttpResponse(html_template.render(context, request))


@login_required(login_url='/authentication/login/')
def pages(request):
    context = {}
    try:
        load_template = request.path.split('/')[-1]

        if load_template == 'admin':
            return HttpResponseRedirect(reverse('admin:index'))
        
        # Récupérer les données du modèle SourceData dans la vue pages
        source_data = SourceData.objects.all()  # Récupérer toutes les entrées
        
        # Ajouter les données au contexte
        context['segment'] = load_template
        context['source_data'] = source_data  # Passer les données à la vue

        html_template = loader.get_template('home/' + load_template)
        return HttpResponse(html_template.render(context, request))

    except template.TemplateDoesNotExist:
        html_template = loader.get_template('home/page-404.html')
        return HttpResponse(html_template.render(context, request))

    except Exception as e:
        # Log the exception
        logger.error(f"An unexpected error occurred: {str(e)}", exc_info=True)

        # Optional: Display the exception details to the user (for development only)
        return HttpResponse(f"An unexpected error occurred: {str(e)}")
