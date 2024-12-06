from django.shortcuts import render
from .models import *
from .decorators import roles_required

@roles_required(['superadmin'])
def index(request):
    source_data = SourceData.objects.all()

    context = {
        'source_data': source_data,
    }
    return render(request, 'sources_data/sources_home.html', context)
