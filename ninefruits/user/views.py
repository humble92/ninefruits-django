from django.contrib.auth.views import LoginView # Removed LogoutView
from django.urls import reverse_lazy
from django.shortcuts import redirect # Ensure redirect is imported
from django.contrib.auth import logout as auth_logout # Added for function view

# HttpResponseRedirect is not used by the new function view or CustomLoginView
# from django.http import HttpResponseRedirect 

class CustomLoginView(LoginView):
    template_name = 'user/login.html'  # Assuming you have a template named login.html
    success_url = reverse_lazy('admin:index')

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

# Removed admin_login_redirect as it's no longer the chosen method.
# from django.http import HttpResponseRedirect
#
# def admin_login_redirect(request):
#     next_url = request.GET.get('next')
#     login_url = reverse_lazy('user:login') 
#     final_login_url_str = str(login_url)
#     if next_url:
#         return HttpResponseRedirect(f"{final_login_url_str}?next={next_url}")
#     return HttpResponseRedirect(final_login_url_str)

from django.shortcuts import render # Added render
from django.contrib.auth.decorators import login_required # Added login_required

@login_required
def mypage_view(request):
    return render(request, 'user/mypage.html')
