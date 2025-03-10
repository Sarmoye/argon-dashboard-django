# errors/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from .models import ErrorEvent, ErrorType, ErrorTicket
from django.http import HttpResponseRedirect
from django.urls import reverse
from .forms import ErrorTypeForm, ErrorEventForm, ErrorTicketForm  # Nous allons créer ces formulaires


def report_error_details(request):
    """Vue pour la deuxième étape: détails de l'événement d'erreur"""
    # Vérifier que la première étape a été complétée
    error_type_id = request.session.get('error_type_id')
    if not error_type_id:
        messages.error(request, "Veuillez d'abord définir le type d'erreur")
        return redirect('ems_app:report_error')
    
    error_type = get_object_or_404(ErrorType, id=error_type_id)
    
    if request.method == 'POST':
        form = ErrorEventForm(request.POST)
        if form.is_valid():
            error_event = form.save(commit=False)
            error_event.error_type = error_type
            error_event.save()
            
            # Stocker l'ID de l'événement d'erreur pour l'étape suivante
            request.session['error_event_id'] = str(error_event.id)
            
            # Rediriger vers la troisième étape
            return redirect('ems_app:create_error_ticket')
    else:
        form = ErrorEventForm(initial={'inserted_by': request.user.username if request.user.is_authenticated else ''})
    
    return render(request, 'errors/report_error_details.html', {'form': form, 'error_type': error_type})

def create_error_ticket(request):
    """Vue pour la troisième étape: création du ticket d'erreur"""
    # Vérifier que les étapes précédentes ont été complétées
    error_type_id = request.session.get('error_type_id')
    error_event_id = request.session.get('error_event_id')
    
    if not error_type_id or not error_event_id:
        messages.error(request, "Veuillez suivre le processus de signalement depuis le début")
        return redirect('ems_app:report_error')
    
    error_type = get_object_or_404(ErrorType, id=error_type_id)
    error_event = get_object_or_404(ErrorEvent, id=error_event_id)
    
    # Vérifier si un ticket existe déjà pour ce type d'erreur
    try:
        ticket = ErrorTicket.objects.get(error_type=error_type)
        messages.info(request, "Un ticket existe déjà pour ce type d'erreur")
        
        # Nettoyer la session et rediriger vers le détail de l'événement
        del request.session['error_type_id']
        del request.session['error_event_id']
        return redirect('ems_app:error_detail', reference_id=error_event.reference_id)
    except ErrorTicket.DoesNotExist:
        # Créer un nouveau ticket si nécessaire
        if request.method == 'POST':
            form = ErrorTicketForm(request.POST)
            if form.is_valid():
                ticket = form.save(commit=False)
                ticket.error_type = error_type
                ticket.save()
                
                # Nettoyer la session et rediriger vers la page de détails
                del request.session['error_type_id']
                del request.session['error_event_id']
                
                messages.success(request, f"Erreur enregistrée avec succès: {error_event.reference_id}")
                return redirect('ems_app:error_detail', reference_id=error_event.reference_id)
        else:
            # Préremplir avec les informations disponibles
            initial_data = {
                'symptomes': f"Premier signalement: {error_type.error_reason}",
                'impact': "À déterminer",
                'services_affectes': error_type.service_name
            }
            form = ErrorTicketForm(initial=initial_data)
    
    return render(request, 'errors/create_error_ticket.html', {'form': form, 'error_type': error_type})


def edit_error_details(request, reference_id):
    """Vue pour modifier les détails d'une erreur"""
    event = get_object_or_404(ErrorEvent, reference_id=reference_id)
    error_type = event.error_type
    
    if request.method == 'POST':
        error_type_form = ErrorTypeForm(request.POST, instance=error_type, prefix='type')
        event_form = ErrorEventForm(request.POST, instance=event, prefix='event')
        
        if error_type_form.is_valid() and event_form.is_valid():
            error_type_form.save()
            event_form.save()
            messages.success(request, f"Les détails de l'erreur {reference_id} ont été mis à jour")
            return redirect('ems_app:error_detail', reference_id=reference_id)
    else:
        error_type_form = ErrorTypeForm(instance=error_type, prefix='type')
        event_form = ErrorEventForm(instance=event, prefix='event')
    
    return render(request, 'errors/edit_error_details.html', {
        'error_type_form': error_type_form,
        'event_form': event_form,
        'event': event
    })

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from .models import ErrorEvent1, ErrorType1, ErrorTicket1
from django.http import HttpResponseRedirect
from django.urls import reverse
from .forms import ErrorType1Form, ErrorEvent1Form, ErrorTicket1Form
import hashlib

def report_error(request):
    """Vue pour signaler une erreur et gérer automatiquement le type d'erreur et le ticket si nécessaire"""
    if request.method == 'POST':
        event_form = ErrorEvent1Form(request.POST)
        
        if event_form.is_valid():
            # Récupérer les données nettoyées du formulaire
            system_name = event_form.cleaned_data['system_name']
            service_type = event_form.cleaned_data['service_type']
            service_name = event_form.cleaned_data['service_name']
            error_reason = event_form.cleaned_data['error_reason']
            
            # Vérifier si un ErrorType1 similaire existe déjà
            # La logique de correspondance utilise le system_name et error_reason comme dans le modèle
            try:
                # Essayer de trouver un type d'erreur similaire
                error_type = ErrorType1.objects.get(
                    system_name=system_name,
                    error_reason=error_reason
                )
                # Type d'erreur existant, on enregistre juste l'occurrence
                is_new_type = False
            except ErrorType1.DoesNotExist:
                # Aucun type similaire, créer un nouveau ErrorType1
                error_type = ErrorType1(
                    system_name=system_name,
                    service_type=service_type,
                    service_name=service_name,
                    error_reason=error_reason,
                    # D'autres champs optionnels peuvent être ajoutés ici
                )
                error_type.save()
                is_new_type = True
                
            # Récupérer le username de l'utilisateur authentifié
            inserted_by = request.user.username if request.user.is_authenticated else 'Système'
            
            # Créer l'événement d'erreur et l'associer au type
            error_event = ErrorEvent1(
                error_type=error_type,
                system_name=system_name,
                service_type=service_type,
                service_name=service_name,
                error_reason=error_reason,
                error_count=event_form.cleaned_data.get('error_count', 1),
                inserted_by=event_form.cleaned_data.get('inserted_by', 'Système'),
                notes=event_form.cleaned_data.get('notes', '')
            )
            error_event.save()
            
            # Si c'est un nouveau type, créer également un ticket
            if is_new_type:
                ticket = ErrorTicket1(
                    error_type=error_type,
                    priorite='P3',  # Valeur par défaut, à ajuster si nécessaire
                    statut='OPEN',
                    niveau_criticite=3,  # Valeur par défaut
                    symptomes=f"Premier signalement: {error_reason}",
                    impact="À déterminer",
                    services_affectes=service_name,
                    # D'autres champs peuvent être initialisés ici
                )
                ticket.save()
                messages.success(request, f"Nouvelle erreur enregistrée avec succès. ID: {error_event.id}")
            else:
                messages.info(request, f"Une erreur similaire a déjà été signalée. Votre occurrence a été enregistrée avec l'ID {error_event.id}")
            
            return redirect('ems_app:error_detail', error_id=error_event.id)
    else:
        # Formulaire vide pour un nouvel événement
        event_form = ErrorEvent1Form(initial={'inserted_by': request.user.username if request.user.is_authenticated else ''})
    
    return render(request, 'errors/report_error.html', {'form': event_form})

def error_detail(request, error_id):
    """Vue pour afficher les détails d'une erreur spécifique"""
    try:
        event = ErrorEvent1.objects.get(id=error_id)
        
        # Récupérer le ticket associé au type d'erreur
        try:
            ticket = ErrorTicket1.objects.get(error_type=event.error_type)
        except ErrorTicket1.DoesNotExist:
            ticket = None
            
        # Récupérer les événements similaires (même type d'erreur)
        similar_events = ErrorEvent1.objects.filter(
            error_type=event.error_type
        ).exclude(id=event.id).order_by('-timestamp')
        
        return render(request, 'errors/error_detail.html', {
            'event': event, 
            'error_type': event.error_type,
            'ticket': ticket,
            'similar_events': similar_events
        })
    except ErrorEvent1.DoesNotExist:
        messages.error(request, f"Erreur avec ID {error_id} non trouvée")
        return redirect('ems_app:error_list')

def error_list(request):
    """Vue pour afficher la liste des erreurs"""
    # Récupérer tous les types d'erreurs
    error_types = ErrorType1.objects.all().order_by('-created_at')
    
    # Pour chaque type, obtenir le nombre d'occurrences et la dernière occurrence
    error_data = []
    for error_type in error_types:
        events = ErrorEvent1.objects.filter(error_type=error_type)
        count = events.count()
        latest = events.order_by('-timestamp').first()
        
        try:
            ticket = ErrorTicket1.objects.get(error_type=error_type)
        except ErrorTicket1.DoesNotExist:
            ticket = None
            
        error_data.append({
            'type': error_type,
            'count': count,
            'latest': latest,
            'ticket': ticket
        })
    
    return render(request, 'errors/error_list.html', {'error_data': error_data})

def add_occurrence(request, type_id):
    """Vue pour ajouter une nouvelle occurrence à un type d'erreur existant"""
    error_type = get_object_or_404(ErrorType1, id=type_id)
    
    if request.method == 'POST':
        form = ErrorEvent1Form(request.POST)
        if form.is_valid():
            # Créer un nouvel événement
            error_event = ErrorEvent1(
                error_type=error_type,
                system_name=error_type.system_name,
                service_type=error_type.service_type,
                service_name=error_type.service_name,
                error_reason=error_type.error_reason,
                error_count=form.cleaned_data.get('error_count', 1),
                inserted_by=form.cleaned_data.get('inserted_by', 'Système'),
                notes=form.cleaned_data.get('notes', '')
            )
            error_event.save()
            
            messages.success(request, f"Nouvelle occurrence ajoutée avec l'ID {error_event.id}")
            return redirect('ems_app:error_detail', error_id=error_event.id)
    else:
        # Pré-remplir le formulaire avec les informations du type d'erreur
        form = ErrorEvent1Form(initial={
            'system_name': error_type.system_name,
            'service_type': error_type.service_type,
            'service_name': error_type.service_name,
            'error_reason': error_type.error_reason,
            'inserted_by': request.user.username if request.user.is_authenticated else '',
            'error_count': 1
        })
    
    return render(request, 'errors/add_occurrence.html', {'form': form, 'error_type': error_type})

def update_ticket(request, ticket_id):
    """Vue pour mettre à jour un ticket d'erreur"""
    ticket = get_object_or_404(ErrorTicket1, id=ticket_id)
    
    if request.method == 'POST':
        form = ErrorTicket1Form(request.POST, instance=ticket)
        if form.is_valid():
            updated_ticket = form.save(commit=False)
            
            # Si le statut change à RESOLVED, mettre à jour la date de résolution
            if updated_ticket.statut == 'RESOLVED' and ticket.statut != 'RESOLVED':
                updated_ticket.date_resolution = timezone.now()
            elif updated_ticket.statut != 'RESOLVED':
                updated_ticket.date_resolution = None
                
            # Capturer l'historique des modifications
            previous_data = {
                'statut': ticket.statut,
                'priorite': ticket.priorite,
                'responsable': ticket.responsable,
                'date_modification': ticket.date_modification.isoformat() if ticket.date_modification else None
            }
            
            # Mettre à jour l'historique
            historique = ticket.historique.copy()
            timestamp = timezone.now().isoformat()
            historique[timestamp] = {
                'previous': previous_data,
                'modified_by': request.user.username if request.user.is_authenticated else 'Système'
            }
            updated_ticket.historique = historique
            
            updated_ticket.save()
            messages.success(request, f"Ticket mis à jour avec succès")
            
            # Rediriger vers les détails du type d'erreur
            return redirect('ems_app:error_type_detail', type_id=ticket.error_type.id)
    else:
        form = ErrorTicket1Form(instance=ticket)
    
    return render(request, 'errors/update_ticket.html', {'form': form, 'ticket': ticket})

def error_type_detail(request, type_id):
    """Vue pour afficher les détails d'un type d'erreur, avec tous ses événements et le ticket associé"""
    error_type = get_object_or_404(ErrorType1, id=type_id)
    
    # Récupérer tous les événements de ce type
    events = ErrorEvent1.objects.filter(error_type=error_type).order_by('-timestamp')
    
    # Récupérer le ticket s'il existe
    try:
        ticket = ErrorTicket1.objects.get(error_type=error_type)
    except ErrorTicket1.DoesNotExist:
        ticket = None
    
    return render(request, 'errors/error_type_detail.html', {
        'error_type': error_type,
        'events': events,
        'ticket': ticket,
        'event_count': events.count()
    })

def edit_error_type(request, type_id):
    """Vue pour modifier un type d'erreur"""
    error_type = get_object_or_404(ErrorType1, id=type_id)
    
    if request.method == 'POST':
        form = ErrorType1Form(request.POST, instance=error_type)
        if form.is_valid():
            form.save()
            messages.success(request, f"Type d'erreur mis à jour avec succès")
            return redirect('ems_app:error_type_detail', type_id=error_type.id)
    else:
        form = ErrorType1Form(instance=error_type)
    
    return render(request, 'errors/edit_error_type.html', {'form': form, 'error_type': error_type})

def edit_error_event(request, error_id):
    """Vue pour modifier un événement d'erreur"""
    event = get_object_or_404(ErrorEvent1, id=error_id)
    
    if request.method == 'POST':
        form = ErrorEvent1Form(request.POST, instance=event)
        if form.is_valid():
            form.save()
            messages.success(request, f"Événement d'erreur mis à jour avec succès")
            return redirect('ems_app:error_detail', error_id=event.id)
    else:
        form = ErrorEvent1Form(instance=event)
    
    return render(request, 'errors/edit_error_event.html', {'form': form, 'event': event})

def create_ticket(request, type_id):
    """Vue pour créer un ticket pour un type d'erreur qui n'en a pas encore"""
    error_type = get_object_or_404(ErrorType1, id=type_id)
    
    # Vérifier si un ticket existe déjà
    try:
        ticket = ErrorTicket1.objects.get(error_type=error_type)
        messages.warning(request, f"Un ticket existe déjà pour ce type d'erreur")
        return redirect('ems_app:error_type_detail', type_id=error_type.id)
    except ErrorTicket1.DoesNotExist:
        pass
    
    if request.method == 'POST':
        form = ErrorTicket1Form(request.POST)
        if form.is_valid():
            ticket = form.save(commit=False)
            ticket.error_type = error_type
            ticket.save()
            
            messages.success(request, f"Ticket créé avec succès")
            return redirect('ems_app:error_type_detail', type_id=error_type.id)
    else:
        # Pré-remplir avec les informations du type d'erreur
        initial_data = {
            'symptomes': f"Problème: {error_type.error_reason}",
            'impact': "À déterminer",
            'services_affectes': error_type.service_name,
            'priorite': 'P3',
            'statut': 'OPEN',
            'niveau_criticite': 3
        }
        form = ErrorTicket1Form(initial=initial_data)
    
    return render(request, 'errors/create_ticket.html', {'form': form, 'error_type': error_type})

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from .models import ErrorEvent, ErrorType, ErrorTicket
from django.http import HttpResponseRedirect
from django.urls import reverse
from .forms import ErrorTypeForm, ErrorEventForm, ErrorTicketForm
import hashlib

def report_error(request):
    """Vue pour signaler une erreur et gérer automatiquement le type d'erreur et le ticket si nécessaire"""
    if request.method == 'POST':
        event_form = ErrorEventForm(request.POST)
        
        if event_form.is_valid():
            # Récupérer les données nettoyées du formulaire
            system_name = event_form.cleaned_data['system_name']
            service_type = event_form.cleaned_data['service_type']
            service_name = event_form.cleaned_data['service_name']
            error_reason = event_form.cleaned_data['error_reason']
            
            # Vérifier si un ErrorType similaire existe déjà
            # La logique de correspondance utilise le system_name et error_reason comme dans le modèle
            try:
                # Essayer de trouver un type d'erreur similaire
                error_type = ErrorType.objects.get(
                    system_name=system_name,
                    error_reason=error_reason
                )
                # Type d'erreur existant, on enregistre juste l'occurrence
                is_new_type = False
            except ErrorType.DoesNotExist:
                # Aucun type similaire, créer un nouveau ErrorType
                error_type = ErrorType(
                    system_name=system_name,
                    service_type=service_type,
                    service_name=service_name,
                    error_reason=error_reason,
                    # D'autres champs optionnels peuvent être ajoutés ici
                )
                error_type.save()
                is_new_type = True
                
            # Récupérer le username de l'utilisateur authentifié
            inserted_by = request.user.username if request.user.is_authenticated else 'Système'
            
            # Créer l'événement d'erreur et l'associer au type
            error_event = ErrorEvent(
                error_type=error_type,
                system_name=system_name,
                service_type=service_type,
                service_name=service_name,
                error_reason=error_reason,
                error_count=event_form.cleaned_data.get('error_count', 1),
                inserted_by=event_form.cleaned_data.get('inserted_by', 'Système'),
                notes=event_form.cleaned_data.get('notes', '')
            )
            error_event.save()
            
            # Si c'est un nouveau type, créer également un ticket
            if is_new_type:
                ticket = ErrorTicket(
                    error_type=error_type,
                    priorite='P3',  # Valeur par défaut, à ajuster si nécessaire
                    statut='OPEN',
                    niveau_criticite=3,  # Valeur par défaut
                    symptomes=f"Premier signalement: {error_reason}",
                    impact="À déterminer",
                    services_affectes=service_name,
                    # D'autres champs peuvent être initialisés ici
                )
                ticket.save()
                messages.success(request, f"Nouvelle erreur enregistrée avec succès. ID: {error_event.id}")
            else:
                messages.info(request, f"Une erreur similaire a déjà été signalée. Votre occurrence a été enregistrée avec l'ID {error_event.id}")
            
            return redirect('ems_app:error_detail', error_id=error_event.id)
    else:
        # Formulaire vide pour un nouvel événement
        event_form = ErrorEventForm(initial={'inserted_by': request.user.username if request.user.is_authenticated else ''})
    
    return render(request, 'errors/report_error.html', {'form': event_form})

def error_detail(request, error_id):
    """Vue pour afficher les détails d'une erreur spécifique"""
    try:
        event = ErrorEvent.objects.get(id=error_id)
        
        # Récupérer le ticket associé au type d'erreur
        try:
            ticket = ErrorTicket.objects.get(error_type=event.error_type)
        except ErrorTicket.DoesNotExist:
            ticket = None
            
        # Récupérer les événements similaires (même type d'erreur)
        similar_events = ErrorEvent.objects.filter(
            error_type=event.error_type
        ).exclude(id=event.id).order_by('-timestamp')
        
        return render(request, 'errors/error_detail.html', {
            'event': event, 
            'error_type': event.error_type,
            'ticket': ticket,
            'similar_events': similar_events
        })
    except ErrorEvent.DoesNotExist:
        messages.error(request, f"Erreur avec ID {error_id} non trouvée")
        return redirect('ems_app:error_list')

def error_list(request):
    """Vue pour afficher la liste des erreurs"""
    # Récupérer tous les types d'erreurs
    error_types = ErrorType.objects.all().order_by('-created_at')
    
    # Pour chaque type, obtenir le nombre d'occurrences et la dernière occurrence
    error_data = []
    for error_type in error_types:
        events = ErrorEvent.objects.filter(error_type=error_type)
        count = events.count()
        latest = events.order_by('-timestamp').first()
        
        try:
            ticket = ErrorTicket.objects.get(error_type=error_type)
        except ErrorTicket.DoesNotExist:
            ticket = None
            
        error_data.append({
            'type': error_type,
            'count': count,
            'latest': latest,
            'ticket': ticket
        })
    
    return render(request, 'errors/error_list.html', {'error_data': error_data})

def add_occurrence(request, type_id):
    """Vue pour ajouter une nouvelle occurrence à un type d'erreur existant"""
    error_type = get_object_or_404(ErrorType, id=type_id)
    
    if request.method == 'POST':
        form = ErrorEventForm(request.POST)
        if form.is_valid():
            # Créer un nouvel événement
            error_event = ErrorEvent(
                error_type=error_type,
                system_name=error_type.system_name,
                service_type=error_type.service_type,
                service_name=error_type.service_name,
                error_reason=error_type.error_reason,
                error_count=form.cleaned_data.get('error_count', 1),
                inserted_by=form.cleaned_data.get('inserted_by', 'Système'),
                notes=form.cleaned_data.get('notes', '')
            )
            error_event.save()
            
            messages.success(request, f"Nouvelle occurrence ajoutée avec l'ID {error_event.id}")
            return redirect('ems_app:error_detail', error_id=error_event.id)
    else:
        # Pré-remplir le formulaire avec les informations du type d'erreur
        form = ErrorEventForm(initial={
            'system_name': error_type.system_name,
            'service_type': error_type.service_type,
            'service_name': error_type.service_name,
            'error_reason': error_type.error_reason,
            'inserted_by': request.user.username if request.user.is_authenticated else '',
            'error_count': 1
        })
    
    return render(request, 'errors/add_occurrence.html', {'form': form, 'error_type': error_type})

def update_ticket(request, ticket_id):
    """Vue pour mettre à jour un ticket d'erreur"""
    ticket = get_object_or_404(ErrorTicket, id=ticket_id)
    
    if request.method == 'POST':
        form = ErrorTicketForm(request.POST, instance=ticket)
        if form.is_valid():
            updated_ticket = form.save(commit=False)
            
            # Si le statut change à RESOLVED, mettre à jour la date de résolution
            if updated_ticket.statut == 'RESOLVED' and ticket.statut != 'RESOLVED':
                updated_ticket.date_resolution = timezone.now()
            elif updated_ticket.statut != 'RESOLVED':
                updated_ticket.date_resolution = None
                
            # Capturer l'historique des modifications
            previous_data = {
                'statut': ticket.statut,
                'priorite': ticket.priorite,
                'responsable': ticket.responsable,
                'date_modification': ticket.date_modification.isoformat() if ticket.date_modification else None
            }
            
            # Mettre à jour l'historique
            historique = ticket.historique.copy()
            timestamp = timezone.now().isoformat()
            historique[timestamp] = {
                'previous': previous_data,
                'modified_by': request.user.username if request.user.is_authenticated else 'Système'
            }
            updated_ticket.historique = historique
            
            updated_ticket.save()
            messages.success(request, f"Ticket mis à jour avec succès")
            
            # Rediriger vers les détails du type d'erreur
            return redirect('ems_app:error_type_detail', type_id=ticket.error_type.id)
    else:
        form = ErrorTicketForm(instance=ticket)
    
    return render(request, 'errors/update_ticket.html', {'form': form, 'ticket': ticket})

def error_type_detail(request, type_id):
    """Vue pour afficher les détails d'un type d'erreur, avec tous ses événements et le ticket associé"""
    error_type = get_object_or_404(ErrorType, id=type_id)
    
    # Récupérer tous les événements de ce type
    events = ErrorEvent.objects.filter(error_type=error_type).order_by('-timestamp')
    
    # Récupérer le ticket s'il existe
    try:
        ticket = ErrorTicket.objects.get(error_type=error_type)
    except ErrorTicket.DoesNotExist:
        ticket = None
    
    return render(request, 'errors/error_type_detail.html', {
        'error_type': error_type,
        'events': events,
        'ticket': ticket,
        'event_count': events.count()
    })

def edit_error_type(request, type_id):
    """Vue pour modifier un type d'erreur"""
    error_type = get_object_or_404(ErrorType, id=type_id)
    
    if request.method == 'POST':
        form = ErrorTypeForm(request.POST, instance=error_type)
        if form.is_valid():
            form.save()
            messages.success(request, f"Type d'erreur mis à jour avec succès")
            return redirect('ems_app:error_type_detail', type_id=error_type.id)
    else:
        form = ErrorTypeForm(instance=error_type)
    
    return render(request, 'errors/edit_error_type.html', {'form': form, 'error_type': error_type})

def edit_error_event(request, error_id):
    """Vue pour modifier un événement d'erreur"""
    event = get_object_or_404(ErrorEvent, id=error_id)
    
    if request.method == 'POST':
        form = ErrorEventForm(request.POST, instance=event)
        if form.is_valid():
            form.save()
            messages.success(request, f"Événement d'erreur mis à jour avec succès")
            return redirect('ems_app:error_detail', error_id=event.id)
    else:
        form = ErrorEventForm(instance=event)
    
    return render(request, 'errors/edit_error_event.html', {'form': form, 'event': event})

def create_ticket(request, type_id):
    """Vue pour créer un ticket pour un type d'erreur qui n'en a pas encore"""
    error_type = get_object_or_404(ErrorType, id=type_id)
    
    # Vérifier si un ticket existe déjà
    try:
        ticket = ErrorTicket.objects.get(error_type=error_type)
        messages.warning(request, f"Un ticket existe déjà pour ce type d'erreur")
        return redirect('ems_app:error_type_detail', type_id=error_type.id)
    except ErrorTicket.DoesNotExist:
        pass
    
    if request.method == 'POST':
        form = ErrorTicketForm(request.POST)
        if form.is_valid():
            ticket = form.save(commit=False)
            ticket.error_type = error_type
            ticket.save()
            
            messages.success(request, f"Ticket créé avec succès")
            return redirect('ems_app:error_type_detail', type_id=error_type.id)
    else:
        # Pré-remplir avec les informations du type d'erreur
        initial_data = {
            'symptomes': f"Problème: {error_type.error_reason}",
            'impact': "À déterminer",
            'services_affectes': error_type.service_name,
            'priorite': 'P3',
            'statut': 'OPEN',
            'niveau_criticite': 3
        }
        form = ErrorTicketForm(initial=initial_data)
    
    return render(request, 'errors/create_ticket.html', {'form': form, 'error_type': error_type})
    
# errors/views.py
# Ajoutez ces imports en haut du fichier
from django.db.models import Count, Avg, F, ExpressionWrapper, fields, Q
from django.utils import timezone
from datetime import timedelta
import json
from django.db.models.functions import Cast, Extract

def dashboard(request):
    """Vue pour le tableau de bord de suivi des erreurs"""
    # Calculer la date il y a 30 jours
    thirty_days_ago = timezone.now() - timedelta(days=30)
    
    # Statistiques générales
    stats = {
        'total_errors': ErrorEvent.objects.count(),
        'active_errors': ErrorEvent.objects.filter(error_type__ticket__statut__in=['OPEN', 'IN_PROGRESS', 'PENDING']).count(),
        'resolved_errors': ErrorEvent.objects.filter(error_type__ticket__statut='RESOLVED').count(),
        'error_types': ErrorType.objects.count(),
        'recent_errors': ErrorEvent.objects.filter(timestamp__gte=thirty_days_ago).count(),
        'avg_resolution_time': ErrorTicket.objects.filter(
            statut='RESOLVED',
            date_resolution__isnull=False
        ).annotate(
            resolution_hours=ExpressionWrapper(
                F('date_resolution') - F('date_creation'), 
                output_field=fields.DurationField()
            )
        ).aggregate(
            avg_hours=Avg(
                ExpressionWrapper(
                    F('resolution_hours') / 3600.0,  # Convertit en heures
                    output_field=fields.FloatField()
                )
            )
        )['avg_hours'] or 0
    }
    
    # Données pour le graphique des erreurs par système
    system_errors = list(ErrorType.objects.values('system_name')
                        .annotate(count=Count('events'))
                        .order_by('-count')[:10])
    
    # Données pour le graphique des tendances temporelles
    # Agréger par jour les 30 derniers jours
    daily_errors = ErrorEvent.objects.filter(
        timestamp__gte=thirty_days_ago
    ).extra({
        'date': "date(timestamp)"
    }).values('date').annotate(
        count=Count('id')
    ).order_by('date')
    
    # Données pour la distribution des priorités
    priority_distribution = list(ErrorTicket.objects.values('priorite')
                               .annotate(count=Count('id'))
                               .order_by('priorite'))
    
    # Temps moyen de résolution par priorité
    resolution_by_priority = list(ErrorTicket.objects.filter(
        statut='RESOLVED',
        date_resolution__isnull=False
    ).values('priorite').annotate(
        avg_hours=Avg(
            ExpressionWrapper(
                Extract('date_resolution', 'epoch') - Extract('date_creation', 'epoch'),
                output_field=fields.FloatField()
            ) / 3600.0
        )
    ).order_by('priorite'))
    
    # Top 5 des erreurs les plus fréquentes
    top_errors = list(ErrorType.objects.annotate(
        events_count=Count('events')
    ).values('system_name', 'error_reason', 'events_count')
    .order_by('-events_count')[:5])
    
    # Préparer les données pour les graphiques
    chart_data = {
        'system_labels': json.dumps([item['system_name'] for item in system_errors]),
        'system_counts': json.dumps([item['count'] for item in system_errors]),
        
        'daily_dates': json.dumps([str(item['date']) for item in daily_errors]),
        'daily_counts': json.dumps([item['count'] for item in daily_errors]),
        
        'priority_labels': json.dumps([dict(ErrorTicket.PRIORITY_CHOICES)[item['priorite']] for item in priority_distribution]),
        'priority_counts': json.dumps([item['count'] for item in priority_distribution]),
        
        'resolution_priority_labels': json.dumps([dict(ErrorTicket.PRIORITY_CHOICES)[item['priorite']] for item in resolution_by_priority]),
        'resolution_priority_times': json.dumps([round(item['avg_hours'], 1) for item in resolution_by_priority]),
    }
    
    # Liste des erreurs récentes non résolues
    recent_unresolved = ErrorEvent.objects.filter(
        error_type__ticket__statut__in=['OPEN', 'IN_PROGRESS']
    ).order_by('-timestamp')[:10]
    
    context = {
        'stats': stats,
        'chart_data': chart_data,
        'top_errors': top_errors,
        'recent_unresolved': recent_unresolved,
    }
    
    return render(request, 'errors/dashboard.html', context)