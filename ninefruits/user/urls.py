from django.urls import path, reverse_lazy
from django.views.generic.base import RedirectView
from .views import CustomLoginView, custom_logout_view, mypage_view, user_info

app_name = 'user'

urlpatterns = [
    path('', RedirectView.as_view(url=reverse_lazy('user:mypage')), name='user_index'),
    path('login/', CustomLoginView.as_view(), name='login'),
    path('logout/', custom_logout_view, name='logout'),
    path('mypage/', mypage_view, name='mypage'),
    path('api/user/info/', user_info, name='user_info'),
]