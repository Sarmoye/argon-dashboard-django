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

    # Créer une fiche pour chaque SourceData validée si elle n'existe pas déjà (en utilisant unique_identifier)
    fiche_erreurs = []
    for data in source_data:
        # Vérifier si une fiche existe déjà pour ce unique_identifier
        fiche_existante = FicheErreur.objects.filter(source_data__unique_identifier=data.unique_identifier).first()

        # Si la fiche n'existe pas, on la crée
        if not fiche_existante:
            fiche = FicheErreur(
                source_data=data,  # Lier la fiche à SourceData via OneToOneField
                system_name=data.system_name,
                service_type=data.service_type,
                service_name=data.service_name,
                error_count=data.error_count,
                error_reason=data.error_reason,
                timestamp=data.timestamp,
                priorite='Normale',  # Valeur par défaut
                statut='Ouvert',  # Valeur par défaut
                source_data_id=data.id,  # Assurez-vous que la fiche est liée à la SourceData
            )
            fiche.save()
            fiche_erreurs.append(fiche)
        else:
            fiche_erreurs.append(fiche_existante)

    # Passer les fiches d'erreurs au template
    return render(request, 'analysis/analysis_home.html', {'fiche_erreurs': fiche_erreurs})


