from datetime import date

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
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

    def test_pagination_splits_across_pages(self):
        for i in range(20):
            Coffee.objects.create(name=f'Coffee {i}', price=1.0, quantity=5, image='https://example.com/x.jpg')
        page1 = self.client.get(reverse('home'), {'page': 1})
        page2 = self.client.get(reverse('home'), {'page': 2})
        self.assertContains(page1, 'Coffee 0')
        self.assertNotContains(page2, 'Coffee 0')
        self.assertNotEqual(page1.content, page2.content)

    def test_pagination_out_of_range_page_does_not_crash(self):
        # Paginator.get_page() should clamp rather than raise EmptyPage -
        # a naive Page.previous_page_number()/next_page_number() call on a
        # boundary page raises EmptyPage uncaught by Django's template
        # engine, so this also guards the _pagination.html include.
        Coffee.objects.create(name='Solo', price=1.0, quantity=5, image='https://example.com/x.jpg')
        for page in [999, 0, 'not-a-number']:
            resp = self.client.get(reverse('home'), {'page': page})
            self.assertEqual(resp.status_code, 200)


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

    def test_pagination_out_of_range_page_does_not_crash(self):
        Biography.objects.create(
            name='Sue', gender='F', place_of_birth='Kampot', date_birth=date(1995, 5, 5),
            role='Barista', email='sue@example.com', mobile='+855987654321', hobby='Coffee', language='English',
        )
        for page in [999, 0, 'not-a-number']:
            resp = self.client.get(reverse('biography'), {'page': page})
            self.assertEqual(resp.status_code, 200)


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

    def test_cart_detail_query_count_does_not_grow_with_item_count(self):
        # cart_detail's select_related('coffee_item') should mean the
        # query count for rendering the cart doesn't grow with the number
        # of distinct items in it - an N+1 regression would add one query
        # per item. Compares counts rather than asserting a fixed magic
        # number, since the exact count includes auth/session queries
        # unrelated to this and would be brittle to pin down directly.
        self.client.post(reverse('add_to_cart', args=[self.coffee.id]))
        with CaptureQueriesContext(connection) as one_item:
            self.client.get(reverse('cart_detail'))

        coffee2 = Coffee.objects.create(name='Latte', price=3.5, quantity=5, image='https://example.com/l.jpg')
        coffee3 = Coffee.objects.create(name='Mocha', price=4.0, quantity=5, image='https://example.com/m.jpg')
        self.client.post(reverse('add_to_cart', args=[coffee2.id]))
        self.client.post(reverse('add_to_cart', args=[coffee3.id]))
        with CaptureQueriesContext(connection) as three_items:
            self.client.get(reverse('cart_detail'))

        self.assertEqual(
            len(one_item), len(three_items),
            "cart_detail query count grew with item count - N+1 regression in select_related('coffee_item')",
        )
