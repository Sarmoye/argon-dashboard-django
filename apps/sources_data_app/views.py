from django.http import HttpResponse
from django.template import loader
from django.contrib.auth.decorators import login_required
from .models import SourceData  # Assurez-vous que le modèle est correctement importé
from django.shortcuts import render

@login_required(login_url='/authentication/login/')
def index(request):
    # Trier les données par timestamp en ordre décroissant
    source_data = SourceData.objects.all().order_by('-timestamp')
    return render(request, 'sources_data/sources_home.html', {'source_data': source_data})
