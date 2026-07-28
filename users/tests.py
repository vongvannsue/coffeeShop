from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from users.models import Profile


class AuthFlowTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='alice', password='strongpass123')

    def test_login_success(self):
        resp = self.client.post(reverse('login'), {'username': 'alice', 'password': 'strongpass123'})
        self.assertRedirects(resp, reverse('home'))
        self.assertIn('_auth_user_id', self.client.session)

    def test_login_failure_wrong_password(self):
        resp = self.client.post(reverse('login'), {'username': 'alice', 'password': 'wrongpass'})
        self.assertEqual(resp.status_code, 200)
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_login_redirects_to_next(self):
        resp = self.client.post(reverse('login'), {
            'username': 'alice', 'password': 'strongpass123', 'next': '/cart/',
        })
        self.assertRedirects(resp, '/cart/')

    def test_login_ignores_unsafe_next(self):
        resp = self.client.post(reverse('login'), {
            'username': 'alice', 'password': 'strongpass123', 'next': 'https://evil.example.com/',
        })
        self.assertRedirects(resp, reverse('home'))

    def test_registration_creates_user_and_profile(self):
        resp = self.client.post(reverse('register'), {
            'username': 'bob', 'password1': 'SuperStrongPass123', 'password2': 'SuperStrongPass123',
        })
        self.assertRedirects(resp, reverse('home'))
        user = User.objects.get(username='bob')
        self.assertTrue(Profile.objects.filter(user=user).exists())

    def test_registration_password_mismatch_rejected(self):
        resp = self.client.post(reverse('register'), {
            'username': 'carol', 'password1': 'SuperStrongPass123', 'password2': 'DifferentPass456',
        })
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(User.objects.filter(username='carol').exists())

    def test_logout_requires_post(self):
        self.client.login(username='alice', password='strongpass123')
        resp = self.client.get(reverse('logout'))
        self.assertEqual(resp.status_code, 405)
        self.assertIn('_auth_user_id', self.client.session)

    def test_logout_post_logs_out(self):
        self.client.login(username='alice', password='strongpass123')
        resp = self.client.post(reverse('logout'))
        self.assertRedirects(resp, reverse('home'))
        self.assertNotIn('_auth_user_id', self.client.session)


class ProfileBackfillTests(TestCase):
    def test_existing_user_created_via_admin_gets_profile(self):
        # Mirrors the BL-02 signal: any User creation path, not just
        # register_view, should end up with a Profile.
        user = User.objects.create_user(username='admin_created', password='strongpass123')
        self.assertTrue(Profile.objects.filter(user=user).exists())
