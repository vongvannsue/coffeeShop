from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import F
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .models import Cart, CartItem, Coffee, Biography

PAGE_SIZE = 12

# Create your views here.
def home(request):
    # return HttpResponse("Holle World!")
    paginator = Paginator(Coffee.objects.order_by('id'), PAGE_SIZE)
    coffee_page = paginator.get_page(request.GET.get('page'))
    return render(request, 'coffee.html', {'coffee': coffee_page})

def Biography_views(request):
    paginator = Paginator(Biography.objects.order_by('id'), PAGE_SIZE)
    biography_page = paginator.get_page(request.GET.get('page'))
    return render(request, 'biography.html', {'biography': biography_page})


@login_required
def cart_detail(request):
    cart, _ = Cart.objects.get_or_create(user=request.user)
    # Evaluate once into a list so both the template loop and the total
    # below reuse this same select_related'd result - Cart.total_price
    # would otherwise run its own separate, unoptimized query per item.
    cart_items = list(cart.items.select_related('coffee_item').all())
    return render(request, 'cart_detail.html', {
        'cart_items': cart_items,
        'total_price': sum(item.total_price for item in cart_items),
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
