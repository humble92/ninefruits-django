from django.apps import AppConfig
from django.contrib import admin
from django.urls import reverse_lazy

class UserConfig(AppConfig):
    name = 'user'

    def ready(self):
        admin.site.login_url = reverse_lazy('user:login')
