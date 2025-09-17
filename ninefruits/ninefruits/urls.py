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
from django.urls import include, path, reverse_lazy
from django.views.generic.base import RedirectView
from django.contrib.auth import views as auth_views

# Authentication URL settings for DRF to redirect to admin page after login
drf_auth_patterns = [
    path('login/', 
        auth_views.LoginView.as_view(
            template_name='rest_framework/login.html',
            redirect_authenticated_user=True,
            next_page=reverse_lazy('admin:index')
        ), name='login'),
    path('logout/', 
        auth_views.LogoutView.as_view(
            next_page=reverse_lazy('rest_framework:login')
        ), name='logout'),
]

urlpatterns = [
    path('', RedirectView.as_view(url=reverse_lazy('user:user_index'))),
    path('admin/', admin.site.urls),

    path('api-auth/', include((drf_auth_patterns, 'rest_framework'))),
    path('api/sis/', include('sis.urls_api')),

    path('user/', include('user.urls')), 
    path('sis/', include('sis.urls')),
]
