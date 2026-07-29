from datetime import date, timedelta

from django.contrib.auth.models import Group, User
from django.core.exceptions import ValidationError
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone

from coffeeapp.models import Biography, CartItem, Coffee, Order, OrderItem


class CoffeeModelTests(TestCase):
    def test_str_returns_name(self):
        coffee = Coffee.objects.create(name='Latte', price=3.5, quantity=5, image='https://example.com/latte.jpg')
        self.assertEqual(str(coffee), 'Latte')

    def test_low_stock_threshold_defaults_to_five(self):
        coffee = Coffee.objects.create(name='Mocha', price=4.0, quantity=20, image='https://example.com/m.jpg')
        self.assertEqual(coffee.low_stock_threshold, 5)


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
        self.assertContains(resp, 'Nothing in this category right now')

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


class CategoryFilterTests(TestCase):
    def setUp(self):
        Coffee.objects.create(name='Doppio', price=3.25, quantity=5, image='https://example.com/d.jpg', category='espresso')
        Coffee.objects.create(name='Nitro Cold Brew', price=5.25, quantity=5, image='https://example.com/n.jpg', category='coldbrew')
        Coffee.objects.create(name='Almond Croissant', price=4.50, quantity=5, image='https://example.com/a.jpg', category='pastries')

    def test_defaults_to_espresso(self):
        resp = self.client.get(reverse('home'))
        self.assertContains(resp, 'Doppio')
        self.assertNotContains(resp, 'Nitro Cold Brew')

    def test_filters_by_requested_category(self):
        resp = self.client.get(reverse('home'), {'category': 'coldbrew'})
        self.assertContains(resp, 'Nitro Cold Brew')
        self.assertNotContains(resp, 'Doppio')

    def test_invalid_category_falls_back_to_espresso(self):
        resp = self.client.get(reverse('home'), {'category': 'not-a-real-category'})
        self.assertContains(resp, 'Doppio')
        self.assertEqual(resp.context['active_category'], 'espresso')

    def test_category_counts_reflect_actual_items(self):
        resp = self.client.get(reverse('home'))
        counts = {c['key']: c['count'] for c in resp.context['categories']}
        self.assertEqual(counts['espresso'], 1)
        self.assertEqual(counts['coldbrew'], 1)
        self.assertEqual(counts['pastries'], 1)
        self.assertEqual(counts['beans'], 0)

    def test_out_of_stock_item_shows_disabled_add_button(self):
        Coffee.objects.create(name='Sold Out Brew', price=4.0, quantity=0, image='https://example.com/s.jpg', category='coldbrew')
        resp = self.client.get(reverse('home'), {'category': 'coldbrew'})
        self.assertContains(resp, 'Sold out')
        self.assertContains(resp, 'disabled')

    def test_pagination_link_preserves_category(self):
        for i in range(20):
            Coffee.objects.create(name=f'Brew {i}', price=1.0, quantity=5, image='https://example.com/x.jpg', category='coldbrew')
        resp = self.client.get(reverse('home'), {'category': 'coldbrew'})
        self.assertContains(resp, 'category=coldbrew&amp;page=2')


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


class CheckoutTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='checkout_user', password='strongpass123')
        self.client.login(username='checkout_user', password='strongpass123')
        self.coffee = Coffee.objects.create(name='Espresso', price=2.5, quantity=5, image='https://example.com/e.jpg')
        self.coffee2 = Coffee.objects.create(name='Latte', price=3.5, quantity=5, image='https://example.com/l.jpg')

    def test_empty_cart_cannot_check_out(self):
        # A brand-new user has no Cart row at all yet - place_order must
        # not 404 on that (it originally did; get_object_or_404 on Cart
        # instead of get_or_create, caught via a real end-to-end request).
        resp = self.client.post(reverse('place_order'), follow=True)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'cart is empty')
        self.assertEqual(Order.objects.count(), 0)

    def test_place_order_requires_post(self):
        resp = self.client.get(reverse('place_order'))
        self.assertEqual(resp.status_code, 405)

    def test_place_order_creates_order_and_snapshots_items(self):
        self.client.post(reverse('add_to_cart', args=[self.coffee.id]))
        self.client.post(reverse('add_to_cart', args=[self.coffee2.id]))
        self.client.post(reverse('add_to_cart', args=[self.coffee2.id]))

        resp = self.client.post(reverse('place_order'))
        order = Order.objects.get(user=self.user)
        self.assertRedirects(resp, reverse('order_confirmation', args=[order.id]))

        items = {i.name: i.quantity for i in order.items.all()}
        self.assertEqual(items, {'Espresso': 1, 'Latte': 2})
        self.assertAlmostEqual(order.subtotal, 2.5 + 3.5 * 2)
        self.assertAlmostEqual(order.tax, order.subtotal * 0.08)
        self.assertAlmostEqual(order.total, order.subtotal + order.tax)

    def test_place_order_clears_cart_without_restoring_stock(self):
        self.client.post(reverse('add_to_cart', args=[self.coffee.id]))
        self.client.post(reverse('place_order'))

        self.coffee.refresh_from_db()
        self.assertEqual(self.coffee.quantity, 4, "stock should stay reserved, not bounce back on checkout")
        self.assertEqual(CartItem.objects.filter(cart__user=self.user).count(), 0)

    def test_order_survives_source_item_deletion(self):
        self.client.post(reverse('add_to_cart', args=[self.coffee.id]))
        self.client.post(reverse('place_order'))
        order = Order.objects.get(user=self.user)

        self.coffee.delete()

        order.refresh_from_db()
        item = order.items.first()
        self.assertIsNone(item.coffee_item)
        self.assertEqual(item.name, 'Espresso')  # snapshot survives even though the source row is gone
        self.assertEqual(order.items.count(), 1)

    def test_confirmation_page_is_owner_only(self):
        self.client.post(reverse('add_to_cart', args=[self.coffee.id]))
        self.client.post(reverse('place_order'))
        order = Order.objects.get(user=self.user)

        User.objects.create_user(username='someone_else', password='strongpass123')
        other_client = self.client_class()
        other_client.login(username='someone_else', password='strongpass123')
        resp = other_client.get(reverse('order_confirmation', args=[order.id]))
        self.assertEqual(resp.status_code, 404)

    def test_confirmation_page_requires_login(self):
        self.client.post(reverse('add_to_cart', args=[self.coffee.id]))
        self.client.post(reverse('place_order'))
        order = Order.objects.get(user=self.user)

        self.client.logout()
        resp = self.client.get(reverse('order_confirmation', args=[order.id]))
        self.assertRedirects(resp, f"{reverse('login')}?next={reverse('order_confirmation', args=[order.id])}")


class OrderStatusManagementTests(TestCase):
    """MB-02: status defaults + staff bulk actions, exercised via the
    Barista group's change_order permission granted in MB-01."""

    def setUp(self):
        buyer = User.objects.create_user(username='status_buyer', password='strongpass123')
        self.order1 = Order.objects.create(user=buyer, subtotal=5, tax=0.5, total=5.5)
        self.order2 = Order.objects.create(user=buyer, subtotal=3, tax=0.3, total=3.3)

        barista = User.objects.create_user(username='barista_ops', password='strongpass123', is_staff=True)
        barista.groups.add(Group.objects.get(name='Barista'))
        self.client.login(username='barista_ops', password='strongpass123')

    def test_new_order_defaults_to_pending(self):
        self.assertEqual(self.order1.status, Order.Status.PENDING)

    def test_bulk_actions_set_expected_status(self):
        for action, expected in [
            ('mark_preparing', Order.Status.PREPARING),
            ('mark_ready', Order.Status.READY),
            ('mark_completed', Order.Status.COMPLETED),
            ('mark_cancelled', Order.Status.CANCELLED),
        ]:
            self.client.post(reverse('admin:coffeeapp_order_changelist'), {
                'action': action,
                '_selected_action': [str(self.order1.pk)],
            })
            self.order1.refresh_from_db()
            self.assertEqual(self.order1.status, expected)

    def test_bulk_action_only_touches_selected_orders(self):
        self.client.post(reverse('admin:coffeeapp_order_changelist'), {
            'action': 'mark_completed',
            '_selected_action': [str(self.order1.pk)],
        })
        self.order1.refresh_from_db()
        self.order2.refresh_from_db()
        self.assertEqual(self.order1.status, Order.Status.COMPLETED)
        self.assertEqual(self.order2.status, Order.Status.PENDING)


class CoffeeRestockTests(TestCase):
    """MB-03: restock bulk action, exercised via the Manager group's
    change_coffee permission granted in MB-01."""

    def setUp(self):
        self.espresso = Coffee.objects.create(
            name='Espresso', price=2.5, quantity=3, image='https://example.com/e.jpg',
        )
        self.latte = Coffee.objects.create(
            name='Latte', price=3.5, quantity=8, image='https://example.com/l.jpg',
        )

        manager = User.objects.create_user(username='manager_ops', password='strongpass123', is_staff=True)
        manager.groups.add(Group.objects.get(name='Manager'))
        self.client.login(username='manager_ops', password='strongpass123')

    def test_restock_action_increments_only_selected(self):
        self.client.post(reverse('admin:coffeeapp_coffee_changelist'), {
            'action': 'restock',
            '_selected_action': [str(self.espresso.pk)],
        })
        self.espresso.refresh_from_db()
        self.latte.refresh_from_db()
        self.assertEqual(self.espresso.quantity, 13)
        self.assertEqual(self.latte.quantity, 8)

    def test_barista_cannot_restock(self):
        # Barista has no change_coffee permission (MB-01) - the action
        # shouldn't be reachable, and quantity must stay untouched.
        barista = User.objects.create_user(username='barista_ops2', password='strongpass123', is_staff=True)
        barista.groups.add(Group.objects.get(name='Barista'))
        self.client.logout()
        self.client.login(username='barista_ops2', password='strongpass123')

        resp = self.client.get(reverse('admin:coffeeapp_coffee_changelist'))
        self.assertEqual(resp.status_code, 403)

        self.espresso.refresh_from_db()
        self.assertEqual(self.espresso.quantity, 3)


class SalesDashboardTests(TestCase):
    """MB-04: dashboard access is gated on coffeeapp.view_dashboard
    (granted to Manager only), and metrics only count completed orders."""

    def setUp(self):
        buyer = User.objects.create_user(username='dash_buyer', password='strongpass123')

        self.recent_completed = Order.objects.create(
            user=buyer, subtotal=10, tax=1, total=11, status=Order.Status.COMPLETED,
        )
        OrderItem.objects.create(order=self.recent_completed, name='Latte', price=3.5, quantity=2)
        OrderItem.objects.create(order=self.recent_completed, name='Espresso', price=2.5, quantity=1)

        # Not completed - must be excluded from totals regardless of range.
        Order.objects.create(user=buyer, subtotal=5, tax=0.5, total=5.5, status=Order.Status.PENDING)

        old_completed = Order.objects.create(
            user=buyer, subtotal=20, tax=2, total=22, status=Order.Status.COMPLETED,
        )
        OrderItem.objects.create(order=old_completed, name='Latte', price=3.5, quantity=5)
        Order.objects.filter(pk=old_completed.pk).update(placed_at=timezone.now() - timedelta(days=60))

        self.manager = User.objects.create_user(
            username='dash_manager', password='strongpass123', is_staff=True,
        )
        self.manager.groups.add(Group.objects.get(name='Manager'))

        self.barista = User.objects.create_user(
            username='dash_barista', password='strongpass123', is_staff=True,
        )
        self.barista.groups.add(Group.objects.get(name='Barista'))

    def test_anonymous_redirected_to_login(self):
        resp = self.client.get(reverse('admin:dashboard'))
        self.assertEqual(resp.status_code, 302)

    def test_barista_cannot_access_dashboard(self):
        self.client.login(username='dash_barista', password='strongpass123')
        resp = self.client.get(reverse('admin:dashboard'))
        self.assertEqual(resp.status_code, 403)

    def test_manager_totals_only_count_completed_orders(self):
        self.client.login(username='dash_manager', password='strongpass123')
        resp = self.client.get(reverse('admin:dashboard'), {'range': 'all'})
        self.assertEqual(resp.status_code, 200)
        self.assertAlmostEqual(resp.context['total_sales'], 11 + 22)
        self.assertEqual(resp.context['order_count'], 2)

    def test_range_filter_excludes_old_orders(self):
        self.client.login(username='dash_manager', password='strongpass123')
        resp = self.client.get(reverse('admin:dashboard'), {'range': 'month'})
        self.assertAlmostEqual(resp.context['total_sales'], 11)
        self.assertEqual(resp.context['order_count'], 1)

    def test_best_sellers_ranked_by_quantity(self):
        self.client.login(username='dash_manager', password='strongpass123')
        resp = self.client.get(reverse('admin:dashboard'), {'range': 'all'})
        best = list(resp.context['best_sellers'])
        self.assertEqual(best[0]['name'], 'Latte')
        self.assertEqual(best[0]['units'], 7)
