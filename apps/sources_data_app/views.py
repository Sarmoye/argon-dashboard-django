from django.shortcuts import render
from .models import *
from .decorators import roles_required
from django import template
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseRedirect
from django.template import loader
from django.urls import reverse

""" @roles_required(['superadmin']) """
def index(request):
    source_data = SourceData.objects.all()
    print(f'source_data ... {source_data}')

    context = {
        'segment': 'index',
        'source_data': source_data,
    }
    html_template = loader.get_template('sources_data/sources_home.html')
    return HttpResponse(html_template.render(context, request))
