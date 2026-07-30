from .views import TAX_RATE, _cart_totals

EMPTY_CART_CONTEXT = {
    'cart_item_count': 0,
    'sidebar_cart_items': [],
    'sidebar_subtotal': 0,
    'sidebar_tax': 0,
    'sidebar_tax_rate_pct': int(TAX_RATE * 100),
    'sidebar_total': 0,
}


def cart_context(request):
    # Powers the persistent order sidebar (coffee.html), so it needs full
    # line items and totals, not just a count - unlike the topbar cart
    # link, which only ever needed the count.
    if not request.user.is_authenticated:
        return EMPTY_CART_CONTEXT
    cart = getattr(request.user, 'cart', None)
    if cart is None:
        return EMPTY_CART_CONTEXT

    cart_items = list(cart.items.select_related('coffee_item').all())
    subtotal, tax, total = _cart_totals(cart_items)
    return {
        'cart_item_count': sum(item.quantity for item in cart_items),
        'sidebar_cart_items': cart_items,
        'sidebar_subtotal': subtotal,
        'sidebar_tax': tax,
        'sidebar_tax_rate_pct': int(TAX_RATE * 100),
        'sidebar_total': total,
    }
