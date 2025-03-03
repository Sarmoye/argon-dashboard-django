from apps.sources_data_app.models import SourceData  # Assurez-vous que le modèle est correctement importé
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

from django.shortcuts import render
from .models import SourceData, FicheErreur

@user_passes_test(
    lambda u: check_user_role(u, ['admin', 'superadmin', 'analyst']), 
    login_url='/authentication/login/'
)
def index(request):
    # Trier les données SourceData par timestamp en ordre décroissant et filtrer par validation_status
    source_data = SourceData.objects.filter(validation_status='Validated').order_by('-timestamp')

    # Dictionnaire pour éviter les doublons (clé = (system_name, error_reason))
    fiche_erreurs_dict = {}

    for data in source_data:
        key = (data.system_name, data.error_reason)  # Clé unique pour chaque combinaison système + erreur

        # Vérifier si une fiche existe déjà en base de données
        fiche_existante = FicheErreur.objects.filter(
            system_name=data.system_name,
            error_reason=data.error_reason
        ).first()

        if not fiche_existante:
            fiche = FicheErreur(
                source_data=data,  # Lier la fiche à SourceData via OneToOneField
                system_name=data.system_name,
                service_type=data.service_type,
                service_name=data.service_name,
                error_count=data.error_count,
                error_reason=data.error_reason,
                priorite='Normale',  # Valeur par défaut
                statut='Ouvert',  # Valeur par défaut
                source_data_id=data.id,  # Assurez-vous que la fiche est liée à la SourceData
                timestamp=data.timestamp,
            )
            fiche.save()
            fiche_erreurs_dict[key] = fiche  # Ajouter au dictionnaire
        else:
            fiche_erreurs_dict[key] = fiche_existante  # Éviter les doublons

    # Convertir en liste avant de passer au template
    fiche_erreurs = list(fiche_erreurs_dict.values())

    return render(request, 'analysis/analysis_home.html', {'fiche_erreurs': fiche_erreurs})


from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from .models import FicheErreur

def update_fiche_erreur(request):
    if request.method == 'POST':
        # print(f"Received data: {request.POST}")
        # Get the fiche erreur instance
        fiche_id = request.POST.get('data_id')
        fiche = get_object_or_404(FicheErreur, id=fiche_id)

        # Get the username from the request
        username = request.user.username  # Assuming the user is authenticated
        
        # Update the analysts field only if the username is not already present
        if fiche.analysts:  # If there are already analysts
            analysts_list = fiche.analysts.split(", ")  # Split into a list
            if username not in analysts_list:  # Check if the username is not already in the list
                fiche.analysts += f", {username}"  # Append the new username
        else:  # If no analysts are present, set the field to the current username
            fiche.analysts = username
        
        # Update basic information
        fiche.system_name = request.POST.get('system_name')
        fiche.service_type = request.POST.get('service_type')
        fiche.service_name = request.POST.get('service_name')
        fiche.error_reason = request.POST.get('error_reason')
        
        # Update status and priority
        fiche.priorite = request.POST.get('priorite')
        fiche.priorite_numerique = request.POST.get('priorite_numerique')
        fiche.niveau_criticite = request.POST.get('niveau_criticite')
        
        # Update error details
        fiche.symptomes_observes = request.POST.get('symptomes_observes')
        fiche.logs_messages = request.POST.get('logs_messages')
        fiche.services_affectes = request.POST.get('services_affectes')
        fiche.cause = request.POST.get('cause')
        
        # Update resolution information
        fiche.solution_proposee = request.POST.get('solution_proposee')
        fiche.solution_implantee = request.POST.get('solution_implantee')
        fiche.efficacite_solution = request.POST.get('efficacite_solution')
        fiche.tests_effectues = request.POST.get('tests_effectues')
        
        # Update technical information
        fiche.code_erreur = request.POST.get('code_erreur')
        fiche.version_systeme = request.POST.get('version_systeme')
        fiche.charge_systeme = request.POST.get('charge_systeme')
        fiche.fichiers_impactes = request.POST.get('fichiers_impactes')
        
        # Update impact assessment
        fiche.impact_financier = request.POST.get('impact_financier')
        fiche.nombre_utilisateurs_impactes = request.POST.get('nombre_utilisateurs_impactes')
        fiche.zone_geographique_affectee = request.POST.get('zone_geographique_affectee')
        
        # Update communication and collaboration
        fiche.canaux_communication = request.POST.get('canaux_communication')
        fiche.notifications_envoyees = bool(request.POST.get('notifications_envoyees'))
        fiche.parties_prenantes = request.POST.get('parties_prenantes')
        
        # Update additional options
        fiche.automatisation_possible = bool(request.POST.get('automatisation_possible'))
        fiche.resolution_automatique_possible = bool(request.POST.get('resolution_automatique_possible'))

        fiche.timestamp_modification = request.POST.get('timestamp')
        fiche.hypotheses = request.POST.get('hypotheses')
        fiche.prochaines_actions = request.POST.get('prochaines_actions')
        fiche.responsable_resolution = request.POST.get('responsable_resolution')
        fiche.commentaires = request.POST.get('commentaires')
        fiche.type_erreur = request.POST.get('type_erreur')
        fiche.statut_resolution = request.POST.get('statut_resolution')
        fiche.statut = request.POST.get('statut')
        fiche.historique_actions = request.POST.get('historique_actions')
        fiche.equipe_responsable = request.POST.get('equipe_responsable')
        fiche.comportement_attendu = request.POST.get('comportement_attendu')
        fiche.comportement_observe = request.POST.get('comportement_observe')
        fiche.delai_resolution = request.POST.get('delai_resolution')
        fiche.delai_ecoule = request.POST.get('delai_ecoule')
        fiche.precedent_incidents_similaires = request.POST.get('precedent_incidents_similaires')
        fiche.audit_log = request.POST.get('audit_log')
        fiche.documentation_associee = request.POST.get('documentation_associee')
        fiche.erreur_normale = bool(request.POST.get('erreur_normale'))
        fiche.impact_utilisateur = request.POST.get('impact_utilisateur')
        fiche.categorie_erreur = request.POST.get('categorie_erreur')
        fiche.frequence = request.POST.get('frequence')
        fiche.etape_detection = request.POST.get('etape_detection')


        print(fiche)
        
        try:
            fiche.save()
            # Success response in JSON format for AJAX
            return JsonResponse({'status': 'success', 'message': 'Error report successfully updated.'})
        except Exception as e:
            # Error response in JSON format for AJAX
            return JsonResponse({'status': 'error', 'message': f'Error updating report: {str(e)}'}, status=400)
    
    # If not POST, return an error response
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=400)
