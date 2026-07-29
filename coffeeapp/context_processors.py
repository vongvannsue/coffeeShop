from django.db.models import Sum


def cart_context(request):
    if not request.user.is_authenticated:
        return {'cart_item_count': 0}
    cart = getattr(request.user, 'cart', None)
    if cart is None:
        return {'cart_item_count': 0}
    count = cart.items.aggregate(total=Sum('quantity'))['total']
    return {'cart_item_count': count or 0}
