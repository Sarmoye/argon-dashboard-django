# sources/views.py

from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .models import SourceData

@login_required(login_url='/authentication/login/')
def index(request):
    # Fetch and order the data
    source_data = SourceData.objects.all().order_by('-timestamp')
    
    # Pagination
    page = request.GET.get('page', 1)  # Get the 'page' parameter from the request
    paginator = Paginator(source_data, 10)  # 10 entries per page
    
    try:
        paginated_data = paginator.page(page)
    except PageNotAnInteger:
        paginated_data = paginator.page(1)
    except EmptyPage:
        paginated_data = paginator.page(paginator.num_pages)

    return render(request, 'sources_data/sources_home.html', {
        'source_data': paginated_data,  # Pass only the current page's data
    })
