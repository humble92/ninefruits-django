from django.test import TestCase
from django.urls import reverse, resolve
from django.contrib.auth.models import User

class UserAuthTests(TestCase):

    def setUp(self):
        # Create a test user
        self.test_user = User.objects.create_user(username='testuser', password='testpassword')

    def test_login_page_renders(self):
        response = self.client.get(reverse('user:login'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'user/login.html')

    def test_valid_login(self):
        # Note: LOGIN_REDIRECT_URL should be set to 'admin:index' or 'user:mypage' in settings for this to pass as is
        # For now, we test if the user is logged in and if the redirect happens.
        # The actual redirect target will be adjusted later based on the new "mypage" requirement.
        login_url = reverse('user:login')
        response = self.client.post(login_url, {'username': 'testuser', 'password': 'testpassword'})
        
        self.assertEqual(response.status_code, 302) # Should redirect
        # Check if user is authenticated
        self.assertTrue(self.client.session.get('_auth_user_id') is not None)

    def test_invalid_login(self):
        login_url = reverse('user:login')
        response = self.client.post(login_url, {'username': 'wronguser', 'password': 'wrongpassword'})
        self.assertEqual(response.status_code, 200) # Stays on login page
        self.assertFalse(self.client.session.get('_auth_user_id')) # Not authenticated
        self.assertContains(response, "Please enter a correct username and password.") # Check for error message

    def test_logout(self):
        # Log the user in first
        self.client.login(username='testuser', password='testpassword')
        self.assertTrue(self.client.session.get('_auth_user_id') is not None) # Pre-condition: user is logged in

        logout_url = reverse('user:logout')
        response = self.client.get(logout_url) # Assuming logout view handles GET
        
        self.assertEqual(response.status_code, 302) # Redirects after logout
        self.assertEqual(response.url, reverse('user:login')) # Redirects to login page
        self.assertFalse(self.client.session.get('_auth_user_id')) # User is logged out

    def test_unauthenticated_admin_access(self):
        admin_url = reverse('admin:index')
        
        # Follow redirects to the final destination
        response_followed = self.client.get(admin_url, follow=True)
        
        # Assert that the final status code is 200 (successful render of login page)
        self.assertEqual(response_followed.status_code, 200)
        
        # Django admin uses its own login page by default
        # So we expect to be redirected to admin:login, not user:login
        self.assertEqual(response_followed.request['PATH_INFO'], '/admin/login/')
        
        # Assert that the admin login template is used
        self.assertTemplateUsed(response_followed, 'admin/login.html')
