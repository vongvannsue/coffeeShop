from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.urls import reverse

from coffeeapp.models import Coffee, Order
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


class RoleGroupPermissionTests(TestCase):
    """MB-01: Barista/Manager groups, created by the 0003 data migration,
    must actually gate admin access — not just exist."""

    def setUp(self):
        self.coffee = Coffee.objects.create(
            name='Latte', price=4.5, quantity=10, image='https://example.com/latte.jpg',
        )
        buyer = User.objects.create_user(username='buyer', password='strongpass123')
        self.order = Order.objects.create(user=buyer, subtotal=4.5, tax=0.45, total=4.95)
        self.order_url = reverse('admin:coffeeapp_order_change', args=[self.order.pk])
        self.coffee_url = reverse('admin:coffeeapp_coffee_change', args=[self.coffee.pk])

    def _staff_user(self, username, group_name=None):
        user = User.objects.create_user(username=username, password='strongpass123', is_staff=True)
        if group_name:
            user.groups.add(Group.objects.get(name=group_name))
        return user

    def test_barista_can_view_order_not_coffee(self):
        self.client.force_login(self._staff_user('barista1', 'Barista'))
        self.assertEqual(self.client.get(self.order_url).status_code, 200)
        self.assertEqual(self.client.get(self.coffee_url).status_code, 403)

    def test_manager_can_view_both(self):
        self.client.force_login(self._staff_user('manager1', 'Manager'))
        self.assertEqual(self.client.get(self.order_url).status_code, 200)
        self.assertEqual(self.client.get(self.coffee_url).status_code, 200)

    def test_staff_with_no_group_sees_neither(self):
        self.client.force_login(self._staff_user('nogroup1'))
        self.assertEqual(self.client.get(self.order_url).status_code, 403)
        self.assertEqual(self.client.get(self.coffee_url).status_code, 403)

    def test_barista_group_has_expected_permissions(self):
        codenames = set(Group.objects.get(name='Barista').permissions.values_list('codename', flat=True))
        self.assertEqual(codenames, {'view_order', 'change_order', 'view_orderitem'})

    def test_manager_group_has_expected_permissions(self):
        # view_dashboard granted separately by MB-04's own migration, not
        # MB-01's - listed here too since this asserts the group's full,
        # current permission set.
        codenames = set(Group.objects.get(name='Manager').permissions.values_list('codename', flat=True))
        self.assertEqual(
            codenames,
            {'view_order', 'change_order', 'view_orderitem', 'view_coffee', 'change_coffee', 'view_dashboard'},
        )
