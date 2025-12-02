"""
URL configuration for core project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

@require_http_methods(["GET"])
def index(request):
    """Root endpoint providing API information"""
    return JsonResponse({
        'message': 'Welcome to Abnormal File Vault API',
        'version': '1.0',
        'endpoints': {
            'files': '/api/files/',
            'admin': '/admin/',
        },
        'documentation': {
            'list_files': 'GET /api/files/',
            'upload_file': 'POST /api/files/',
            'get_file': 'GET /api/files/<id>/',
            'update_file': 'PATCH /api/files/<id>/',
            'delete_file': 'DELETE /api/files/<id>/',
            'download_file': 'GET /api/files/<id>/download/',
            'storage_stats': 'GET /api/files/storage_stats/',
            'file_types': 'GET /api/files/file_types/',
        }
    })

urlpatterns = [
    path('', index, name='index'),
    path('admin/', admin.site.urls),
    path('api/', include('files.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
