from django.urls import path
from .views import CustomLoginView, custom_logout_view # Changed import

app_name = 'user'

urlpatterns = [
    path('login/', CustomLoginView.as_view(), name='login'),
    path('logout/', custom_logout_view, name='logout'), # Changed to function view
]