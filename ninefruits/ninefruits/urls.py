"""ninefruits URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.0/topics/http/urls/
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
from django.urls import include, path, reverse_lazy # Ensure reverse_lazy is imported

from django.contrib import admin
from django.urls import include, path, reverse_lazy # Ensure reverse_lazy is imported
# RedirectView import is removed as it's no longer used.
# from django.views.generic.base import RedirectView 

# The line admin.site.login_url = reverse_lazy('user:login') is removed from here.
# It's now handled in user/apps.py.

urlpatterns = [
    # The RedirectView path for 'admin/login/' is removed.
    path('admin/', admin.site.urls),
    path('api-auth/', include('rest_framework.urls')),
    # Using 'user.urls' as it has been confirmed to work.
    path('user/', include('user.urls')), 
    path('', include('sis.urls')),
]
