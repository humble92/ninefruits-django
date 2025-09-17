from django.contrib.auth.views import LoginView
from django.urls import reverse_lazy
from django.shortcuts import redirect, render
from django.contrib.auth import logout as auth_logout
from django.contrib.auth.decorators import login_required

class CustomLoginView(LoginView):
    template_name = 'user/login.html'

    # It is covered by LOGIN_REDIRECT_URL in settings.py
    # def get_success_url(self):
    #     return reverse_lazy('user:mypage')

    def form_invalid(self, form):
        # You can add custom logic here for invalid login attempts if needed
        # For example, logging the attempt or displaying a specific message
        return super().form_invalid(form)

    def form_valid(self, form):
        # This method is called when valid credentials are submitted
        # You can add custom logic here before redirecting
        return super().form_valid(form)

# Removed class-based CustomLogoutView
# class CustomLogoutView(LogoutView):
#     next_page = reverse_lazy('user:login')
# 
#     def get(self, request, *args, **kwargs):
#         # Allow logout via GET request
#         return self.post(request, *args, **kwargs)

def custom_logout_view(request):
    auth_logout(request)
    return redirect(reverse_lazy('user:login'))

@login_required
def mypage_view(request):
    return render(request, 'user/mypage.html')
