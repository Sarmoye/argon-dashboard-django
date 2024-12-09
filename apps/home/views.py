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
from apps.sources_data_app.models import SourceData  # Import du modèle

logger = logging.getLogger(__name__)

@login_required(login_url='/authentication/login/')
def index(request):
    context = {'segment': 'index'}

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
