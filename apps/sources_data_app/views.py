from django.http import HttpResponse
from django.template import loader
from django.contrib.auth.decorators import login_required
from .models import SourceData  # Assurez-vous que le modèle est correctement importé

@login_required(login_url='/login/')  # Vérifie si l'utilisateur est authentifié
def index(request):
    # Récupération des données depuis le modèle SourceData
    source_data = SourceData.objects.all()
    print(f'source_data ... {source_data}')  # Debug pour voir les données dans la console

    # Passer les données au template
    context = {
        'segment': 'index',
        'source_data': source_data,
    }

    # Chargement et rendu du template
    html_template = loader.get_template('sources_data/sources_home.html')
    return HttpResponse(html_template.render(context, request))
