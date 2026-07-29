from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count, F
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .models import Cart, CartItem, Coffee, Biography, Order, OrderItem

PAGE_SIZE = 12

CATEGORY_META = {
    Coffee.Category.ESPRESSO: {
        'eyebrow': 'Pulled to order',
        'sub': 'Double shots, 18–20g in, 20s pour. Every drink starts here.',
    },
    Coffee.Category.COLD_BREW: {
        'eyebrow': 'Steeped 18 hours',
        'sub': 'Always over ice, always low-acid. Brewed overnight in small batches.',
    },
    Coffee.Category.PASTRIES: {
        'eyebrow': 'From the oven',
        'sub': 'Baked fresh before sunrise, gone by early afternoon most days.',
    },
    Coffee.Category.BEANS: {
        'eyebrow': '12oz bags',
        'sub': 'Roasted Tuesdays and Fridays. Ground to order or whole bean.',
    },
    Coffee.Category.OFFERS: {
        'eyebrow': 'Bundled to save',
        'sub': 'Pair a drink with something from the case — while supplies last.',
    },
}

# Create your views here.
def home(request):
    category_counts = dict(
        Coffee.objects.values_list('category').annotate(count=Count('id')).order_by()
    )
    categories = [
        {
            'key': key,
            'label': label,
            'count': category_counts.get(key, 0),
        }
        for key, label in Coffee.Category.choices
    ]

    requested = request.GET.get('category')
    valid_keys = {c['key'] for c in categories}
    active_category = requested if requested in valid_keys else Coffee.Category.ESPRESSO

    paginator = Paginator(Coffee.objects.filter(category=active_category).order_by('id'), PAGE_SIZE)
    coffee_page = paginator.get_page(request.GET.get('page'))

    return render(request, 'coffee.html', {
        'coffee': coffee_page,
        'categories': categories,
        'active_category': active_category,
        'active_category_label': dict(Coffee.Category.choices).get(active_category, ''),
        'category_meta': CATEGORY_META.get(active_category, {}),
    })

def Biography_views(request):
    paginator = Paginator(Biography.objects.order_by('id'), PAGE_SIZE)
    biography_page = paginator.get_page(request.GET.get('page'))
    return render(request, 'biography.html', {'biography': biography_page})


TAX_RATE = 0.08


def _cart_totals(cart_items):
    subtotal = sum(item.total_price for item in cart_items)
    tax = subtotal * TAX_RATE
    return subtotal, tax, subtotal + tax


@login_required
def cart_detail(request):
    cart, _ = Cart.objects.get_or_create(user=request.user)
    # Evaluate once into a list so both the template loop and the totals
    # below reuse this same select_related'd result - Cart.total_price
    # would otherwise run its own separate, unoptimized query per item.
    cart_items = list(cart.items.select_related('coffee_item').all())
    subtotal, tax, total = _cart_totals(cart_items)
    return render(request, 'cart_detail.html', {
        'cart_items': cart_items,
        'subtotal': subtotal,
        'tax': tax,
        'tax_rate_pct': int(TAX_RATE * 100),
        'total_price': total,
    })


@login_required
@require_POST
def add_to_cart(request, coffee_id):
    with transaction.atomic():
        coffee_item = get_object_or_404(Coffee.objects.select_for_update(), pk=coffee_id)
        if coffee_item.quantity < 1:
            messages.error(request, f"{coffee_item.name} is out of stock.")
            return redirect('cart_detail')

        cart, _ = Cart.objects.get_or_create(user=request.user)
        item, _ = CartItem.objects.get_or_create(cart=cart, coffee_item=coffee_item, defaults={'quantity': 0})
        item.quantity = F('quantity') + 1
        item.save(update_fields=['quantity'])
        coffee_item.quantity = F('quantity') - 1
        coffee_item.save(update_fields=['quantity'])
    return redirect('cart_detail')


@login_required
@require_POST
def remove_from_cart(request, coffee_id):
    with transaction.atomic():
        cart = get_object_or_404(Cart, user=request.user)
        item = get_object_or_404(CartItem.objects.select_for_update(), cart=cart, coffee_item_id=coffee_id)
        coffee_item = Coffee.objects.select_for_update().get(pk=coffee_id)

        if item.quantity <= 1:
            item.delete()
        else:
            item.quantity = F('quantity') - 1
            item.save(update_fields=['quantity'])
        coffee_item.quantity = F('quantity') + 1
        coffee_item.save(update_fields=['quantity'])
    return redirect('cart_detail')


@login_required
@require_POST
def delete_from_cart(request, coffee_id):
    with transaction.atomic():
        cart = get_object_or_404(Cart, user=request.user)
        item = get_object_or_404(CartItem.objects.select_for_update(), cart=cart, coffee_item_id=coffee_id)
        coffee_item = Coffee.objects.select_for_update().get(pk=coffee_id)

        coffee_item.quantity = F('quantity') + item.quantity
        coffee_item.save(update_fields=['quantity'])
        item.delete()
    return redirect('cart_detail')


@login_required
@require_POST
def clear_cart(request):
    with transaction.atomic():
        cart = get_object_or_404(Cart, user=request.user)
        for item in cart.items.select_for_update():
            coffee_item = Coffee.objects.select_for_update().get(pk=item.coffee_item_id)
            coffee_item.quantity = F('quantity') + item.quantity
            coffee_item.save(update_fields=['quantity'])
        cart.items.all().delete()
    return redirect('cart_detail')


@login_required
@require_POST
def place_order(request):
    cart, _ = Cart.objects.get_or_create(user=request.user)
    cart_items = list(cart.items.select_related('coffee_item').all())
    if not cart_items:
        messages.error(request, "Your cart is empty.")
        return redirect('cart_detail')

    subtotal, tax, total = _cart_totals(cart_items)

    with transaction.atomic():
        order = Order.objects.create(user=request.user, subtotal=subtotal, tax=tax, total=total)
        OrderItem.objects.bulk_create([
            OrderItem(
                order=order,
                coffee_item=item.coffee_item,
                name=item.coffee_item.name,
                price=item.coffee_item.price,
                quantity=item.quantity,
            )
            for item in cart_items
        ])
        # Stock was already decremented when these were added to cart (see
        # add_to_cart) - placing the order confirms that reservation, so
        # clear the cart without restoring quantity (unlike remove/delete/
        # clear, which represent changing your mind, not completing a sale).
        cart.items.all().delete()

    return redirect('order_confirmation', order_id=order.id)


@login_required
def order_confirmation(request, order_id):
    order = get_object_or_404(
        Order.objects.prefetch_related('items').filter(user=request.user),
        id=order_id,
    )
    return render(request, 'order_confirmation.html', {'order': order})
