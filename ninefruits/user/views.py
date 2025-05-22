from django.contrib.auth.views import LoginView, LogoutView
from django.urls import reverse_lazy

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

class CustomLogoutView(LogoutView):
    next_page = reverse_lazy('user:login')
