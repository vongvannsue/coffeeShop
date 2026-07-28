from datetime import date

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from coffeeapp.models import Biography, CartItem, Coffee


class CoffeeModelTests(TestCase):
    def test_str_returns_name(self):
        coffee = Coffee.objects.create(name='Latte', price=3.5, quantity=5, image='https://example.com/latte.jpg')
        self.assertEqual(str(coffee), 'Latte')


class BiographyModelTests(TestCase):
    def _make(self, **overrides):
        fields = dict(
            name='Jane', gender='F', place_of_birth='Phnom Penh', date_birth=date(1990, 1, 1),
            role='Owner', email='jane@example.com', mobile='+855123456789', hobby='Reading', language='Khmer',
        )
        fields.update(overrides)
        return Biography(**fields)

    def test_str_returns_name(self):
        bio = self._make()
        bio.save()
        self.assertEqual(str(bio), 'Jane')

    def test_invalid_mobile_rejected_by_validator(self):
        bio = self._make(mobile='not-a-phone!!')
        with self.assertRaises(ValidationError):
            bio.full_clean()

    def test_valid_mobile_formats_accepted(self):
        for mobile in ['+855123456789', '012-345-678', '(012) 345 678']:
            bio = self._make(mobile=mobile)
            bio.full_clean()  # should not raise


class HomeViewTests(TestCase):
    def test_empty_state(self):
        resp = self.client.get(reverse('home'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'No products available')

    def test_lists_coffee(self):
        Coffee.objects.create(name='Mocha', price=4.0, quantity=3, image='https://example.com/mocha.jpg')
        resp = self.client.get(reverse('home'))
        self.assertContains(resp, 'Mocha')


class BiographyViewTests(TestCase):
    def test_empty_state(self):
        resp = self.client.get(reverse('biography'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'No data available')

    def test_lists_biography(self):
        Biography.objects.create(
            name='Sue', gender='F', place_of_birth='Kampot', date_birth=date(1995, 5, 5),
            role='Barista', email='sue@example.com', mobile='+855987654321', hobby='Coffee', language='English',
        )
        resp = self.client.get(reverse('biography'))
        self.assertContains(resp, 'Sue')


class CartPermissionTests(TestCase):
    """Anonymous users must be sent to login, never allowed into the cart."""

    def setUp(self):
        self.coffee = Coffee.objects.create(name='Espresso', price=2.5, quantity=5, image='https://example.com/e.jpg')

    def test_cart_detail_requires_login(self):
        resp = self.client.get(reverse('cart_detail'))
        self.assertRedirects(resp, f"{reverse('login')}?next={reverse('cart_detail')}")

    def test_add_to_cart_requires_login(self):
        url = reverse('add_to_cart', args=[self.coffee.id])
        resp = self.client.post(url)
        self.assertRedirects(resp, f"{reverse('login')}?next={url}")


class CartFlowTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='cart_user', password='strongpass123')
        self.client.login(username='cart_user', password='strongpass123')
        self.coffee = Coffee.objects.create(name='Espresso', price=2.5, quantity=5, image='https://example.com/e.jpg')

    def test_add_to_cart_requires_post(self):
        resp = self.client.get(reverse('add_to_cart', args=[self.coffee.id]))
        self.assertEqual(resp.status_code, 405)

    def test_add_to_cart_decrements_stock(self):
        resp = self.client.post(reverse('add_to_cart', args=[self.coffee.id]))
        self.assertRedirects(resp, reverse('cart_detail'))
        self.coffee.refresh_from_db()
        self.assertEqual(self.coffee.quantity, 4)
        item = CartItem.objects.get(cart__user=self.user, coffee_item=self.coffee)
        self.assertEqual(item.quantity, 1)

    def test_add_to_cart_twice_accumulates_quantity(self):
        self.client.post(reverse('add_to_cart', args=[self.coffee.id]))
        self.client.post(reverse('add_to_cart', args=[self.coffee.id]))
        self.coffee.refresh_from_db()
        self.assertEqual(self.coffee.quantity, 3)
        item = CartItem.objects.get(cart__user=self.user, coffee_item=self.coffee)
        self.assertEqual(item.quantity, 2)

    def test_remove_from_cart_restores_one_unit(self):
        self.client.post(reverse('add_to_cart', args=[self.coffee.id]))
        resp = self.client.post(reverse('remove_from_cart', args=[self.coffee.id]))
        self.assertRedirects(resp, reverse('cart_detail'))
        self.coffee.refresh_from_db()
        self.assertEqual(self.coffee.quantity, 5)
        self.assertFalse(CartItem.objects.filter(cart__user=self.user, coffee_item=self.coffee).exists())

    def test_delete_from_cart_restores_full_quantity(self):
        self.client.post(reverse('add_to_cart', args=[self.coffee.id]))
        self.client.post(reverse('add_to_cart', args=[self.coffee.id]))
        resp = self.client.post(reverse('delete_from_cart', args=[self.coffee.id]))
        self.assertRedirects(resp, reverse('cart_detail'))
        self.coffee.refresh_from_db()
        self.assertEqual(self.coffee.quantity, 5)
        self.assertFalse(CartItem.objects.filter(cart__user=self.user, coffee_item=self.coffee).exists())

    def test_clear_cart_restores_all_stock(self):
        coffee2 = Coffee.objects.create(name='Latte', price=3.5, quantity=3, image='https://example.com/l.jpg')
        self.client.post(reverse('add_to_cart', args=[self.coffee.id]))
        self.client.post(reverse('add_to_cart', args=[coffee2.id]))
        resp = self.client.post(reverse('clear_cart'))
        self.assertRedirects(resp, reverse('cart_detail'))
        self.coffee.refresh_from_db()
        coffee2.refresh_from_db()
        self.assertEqual(self.coffee.quantity, 5)
        self.assertEqual(coffee2.quantity, 3)
        self.assertEqual(CartItem.objects.filter(cart__user=self.user).count(), 0)

    def test_add_to_cart_out_of_stock_rejected(self):
        self.coffee.quantity = 0
        self.coffee.save()
        resp = self.client.post(reverse('add_to_cart', args=[self.coffee.id]), follow=True)
        self.assertContains(resp, 'out of stock')
        self.assertFalse(CartItem.objects.filter(cart__user=self.user, coffee_item=self.coffee).exists())

    def test_stock_guard_rejects_add_once_exhausted(self):
        # NOTE: this proves the business logic (reject once quantity hits 0)
        # sequentially, in a single thread/connection - it is NOT a true
        # concurrent-race test. Django's sqlite3 backend reports
        # has_select_for_update = False, so select_for_update() is a no-op
        # for row locking there (confirmed: it doesn't raise, it just
        # doesn't lock). A real concurrency test needs TransactionTestCase
        # with separate threads/connections against a backend with real
        # row locking (Postgres, once BL-13 lands) - SQLite's own coarse
        # file-level write lock would serialize concurrent writers
        # regardless of whether select_for_update() does anything, so a
        # threaded test here would validate SQLite's locking, not this
        # application's atomic-transaction design.
        self.coffee.quantity = 1
        self.coffee.save()
        self.client.post(reverse('add_to_cart', args=[self.coffee.id]))
        resp = self.client.post(reverse('add_to_cart', args=[self.coffee.id]), follow=True)
        self.coffee.refresh_from_db()
        self.assertEqual(self.coffee.quantity, 0)
        self.assertContains(resp, 'out of stock')
        item = CartItem.objects.get(cart__user=self.user, coffee_item=self.coffee)
        self.assertEqual(item.quantity, 1)
