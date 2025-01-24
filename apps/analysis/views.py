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

@user_passes_test(
    lambda u: check_user_role(u, ['admin', 'superadmin']), 
    login_url='/authentication/login/'
)
def index(request):
    # Filtrer par validation_status et récupérer des erreurs distinctes
    source_data = SourceData.objects.filter(validation_status='Validated').order_by('-timestamp').distinct('error_reason')
    return render(request, 'sources_data/sources_home.html', {'source_data': source_data})

