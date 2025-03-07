# errors/views.py
from django.shortcuts import render, redirect
from django.contrib import messages
from django.utils import timezone
from .models import ErrorEvent, ErrorType, ErrorTicket

def report_error(request):
    """Vue pour signaler une nouvelle erreur"""
    if request.method == 'POST':
        # Récupérer les données du formulaire
        system_name = request.POST.get('system_name')
        service_type = request.POST.get('service_type')
        service_name = request.POST.get('service_name')
        error_reason = request.POST.get('error_reason')
        code_erreur = request.POST.get('code_erreur', '')
        error_count = int(request.POST.get('error_count', 1))
        domain = request.POST.get('domain')
        logs = request.POST.get('logs', '')
        version_system = request.POST.get('version_system', '')
        comportement_attendu = request.POST.get('comportement_attendu', '')
        inserted_by = request.POST.get('inserted_by')
        notes = request.POST.get('notes', '')
        correction_automatique = 'correction_automatique' in request.POST
        
        # Chercher ou créer un ErrorType correspondant
        error_type, created = ErrorType.objects.get_or_create(
            system_name=system_name,
            error_reason=error_reason,
            defaults={
                'service_type': service_type,
                'service_name': service_name,
                'code_erreur': code_erreur,
                'comportement_attendu': comportement_attendu,
                'correction_automatique': correction_automatique
            }
        )
        
        # Créer un ErrorEvent
        error_event = ErrorEvent.objects.create(
            error_type=error_type,
            error_count=error_count,
            domain=domain,
            logs=logs,
            version_system=version_system,
            inserted_by=inserted_by,
            notes=notes
        )
        
        # Si on vient de créer un nouveau ErrorType, créer aussi un ErrorTicket associé
        if created:
            ErrorTicket.objects.create(
                error_type=error_type,
                symptomes=f"Premier signalement: {error_reason}",
                impact="À déterminer",
                services_affectes=service_name
            )
            messages.success(request, f"Erreur enregistrée avec un nouveau ticket: {error_event.reference_id}")
        else:
            messages.success(request, f"Erreur enregistrée: {error_event.reference_id}")
        
        return redirect('error_list')  # Rediriger vers la liste des erreurs
        
    return render(request, 'errors/report_error.html')

def error_list(request):
    """Vue pour afficher la liste des erreurs récentes"""
    events = ErrorEvent.objects.all().order_by('-timestamp')[:50]
    return render(request, 'errors/error_list.html', {'events': events})

def error_detail(request, reference_id):
    """Vue pour afficher les détails d'une erreur spécifique"""
    try:
        event = ErrorEvent.objects.get(reference_id=reference_id)
        return render(request, 'errors/error_detail.html', {'event': event})
    except ErrorEvent.DoesNotExist:
        messages.error(request, f"Erreur avec référence {reference_id} non trouvée")
        return redirect('error_list')