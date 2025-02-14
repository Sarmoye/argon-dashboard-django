from django.http import HttpResponse
from django.template import loader
from django.contrib.auth.decorators import login_required
from .models import SourceData  # Assurez-vous que le modèle est correctement importé
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

@user_passes_test(
    lambda u: check_user_role(u, ['admin', 'superadmin']), 
    login_url='/authentication/login/'
)
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


from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from .models import SourceData
import json

@login_required
@require_POST
def submit_validation(request):
    try:
        # Parse form data
        data = json.loads(request.body)
        
        # Get the selected source data entries (you might want to pass specific IDs)
        source_date = data.get('source_date')
        systeme = data.get('systeme')
        validation_status = data.get('validation_status')
        
        # Find source data entries to update
        source_entries = SourceData.objects.filter(
            system_name=systeme,
            timestamp__date=source_date
        )
        
        # Update validation status
        updated_count = source_entries.update(
            validation_status=validation_status,
            admin_notes=f"Validated by {request.user.username}"
        )
        
        return JsonResponse({
            'success': True, 
            'updated_count': updated_count
        })
    
    except Exception as e:
        return JsonResponse({
            'success': False, 
            'error': str(e)
        }, status=400)

