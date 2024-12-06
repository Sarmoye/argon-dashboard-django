# authentication/decorators.py
from django.shortcuts import render

def roles_required(roles):
    def decorator(view_func):
        def _wrapped_view(request, *args, **kwargs):
            # Vérifier si l'utilisateur a le bon rôle ou est superuser
            if request.user.role not in roles and not request.user.is_superuser:
                # Retourner un template personnalisé en cas de refus
                return render(request, '403.html', {'message': "Vous n'avez pas la permission d'accéder à cette page"}, status=403)
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator