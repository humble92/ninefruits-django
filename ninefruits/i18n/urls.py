from django.urls import path

from . import views

app_name = "i18n"

urlpatterns = [path("locale/", views.update_locale, name="locale-update")]
