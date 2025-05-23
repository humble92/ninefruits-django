from django.apps import AppConfig
from django.contrib import admin
from django.urls import reverse_lazy
# Removed unused imports: redirect, urlencode

class UserConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'user' # Ensure this is 'user'

    def ready(self):
        admin.site.login_url = reverse_lazy('user:login')
        # The custom_admin_login function and admin.site.login override are removed.
