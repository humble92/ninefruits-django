from django.urls import path
from django.views.generic import TemplateView

app_name = 'sis'

urlpatterns = [
    path('', TemplateView.as_view(template_name='sis/index.html')),
]