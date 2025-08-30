from django.urls import path
from .views import CustomLoginView, custom_logout_view, mypage_view # Added mypage_view

app_name = 'user'

urlpatterns = [
    path('login/', CustomLoginView.as_view(), name='login'),
    path('logout/', custom_logout_view, name='logout'),
    path('mypage/', mypage_view, name='mypage'), # Added mypage URL
]