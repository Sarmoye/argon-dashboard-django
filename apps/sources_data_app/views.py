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

@login_required(login_url='/authentication/login/')
def get_source_data(request):
    # Retrieve and order the data
    source_data = SourceData.objects.all().order_by('-timestamp')

    # Prepare the data for JSON response
    data = list(source_data.values('id', 'system_name', 'domain', 'service_type', 'service_name', 
                                   'error_count', 'error_reason', 'source_type', 'timestamp', 
                                   'validation_status', 'processed_flag', 'admin_notes', 'inserted_by'))
    
    return JsonResponse({'data': data})

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
from .models import SourceData  # Remplacez par le nom réel de votre modèle

@csrf_exempt
def apply_validation(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            validation_date = data['validation_date']
            validation_status = data['validation_status']
            admin_notes = data['admin_notes']

            # Mise à jour des lignes dans la base de données
            SourceData.objects.filter(timestamp__date=validation_date).update(
                validation_status=validation_status,
                admin_notes=admin_notes
            )

            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    return JsonResponse({'success': False, 'error': 'Invalid request method'})

