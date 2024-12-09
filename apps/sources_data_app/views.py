from django.http import HttpResponse
from django.template import loader
from django.contrib.auth.decorators import login_required
from .models import SourceData  # Assurez-vous que le modèle est correctement importé
from django.shortcuts import render

@login_required(login_url='/login/')
def index(request):
    source_data = SourceData.objects.all()
    return render(request, 'sources_data/sources_home.html', {'source_data': source_data})
