from django.conf import settings
from django.core.validators import RegexValidator
from django.db import models

phone_validator = RegexValidator(
    regex=r'^\+?[0-9 ()-]{7,20}$',
    message="Enter a valid phone number (digits, spaces, '+', '-', '(', ')' only).",
)

# Coffee models
class Coffee(models.Model):
    class Category(models.TextChoices):
        ESPRESSO = 'espresso', 'Espresso'
        COLD_BREW = 'coldbrew', 'Cold Brew'
        PASTRIES = 'pastries', 'Pastries'
        BEANS = 'beans', 'Beans'
        OFFERS = 'offers', 'Special Offers'

    name = models.CharField(max_length=255)
    price = models.FloatField()
    quantity = models.IntegerField()
    image = models.URLField()
    category = models.CharField(max_length=20, choices=Category.choices, default=Category.ESPRESSO)
    # Per-item, not global (MB-03 decision): a bean SKU and a pastry have
    # very different reorder points.
    low_stock_threshold = models.PositiveIntegerField(default=5)

    def __str__(self):
        return self.name

# Cart models — one cart per user, decremented from Coffee.quantity as items
# are added (reserved) and restored as they're removed (see BL-03 decision:
# DB-backed, tied to request.user, since auth already works end-to-end and
# it avoids merging an anonymous session cart on login).
class Cart(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='cart')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username}'s cart"

    @property
    def total_price(self):
        return sum(item.total_price for item in self.items.all())


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    coffee_item = models.ForeignKey(Coffee, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)

    class Meta:
        unique_together = ('cart', 'coffee_item')

    def __str__(self):
        return f"{self.quantity} x {self.coffee_item.name}"

    @property
    def total_price(self):
        return self.coffee_item.price * self.quantity


# Order models — a permanent record of a placed order, snapshotting name/
# price on each line so history stays correct even if the Coffee item is
# later renamed, repriced, or deleted. Stock was already decremented when
# items were added to cart (see CartItem above); placing an order confirms
# that reservation rather than touching Coffee.quantity again.
class Order(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        PREPARING = 'preparing', 'Preparing'
        READY = 'ready', 'Ready'
        COMPLETED = 'completed', 'Completed'
        CANCELLED = 'cancelled', 'Cancelled'

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='orders')
    placed_at = models.DateTimeField(auto_now_add=True)
    subtotal = models.FloatField()
    tax = models.FloatField()
    total = models.FloatField()
    # Free-form (MB-02 decision): any status settable at any time, no
    # enforced sequence — staff are trusted not to mis-click.
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING, db_index=True)

    class Meta:
        ordering = ['-placed_at']
        permissions = [
            ('view_dashboard', 'Can view sales dashboard'),
        ]

    def __str__(self):
        return f'Order #{self.id} — {self.user.username}'

    @property
    def display_number(self):
        return f'HB-{self.id:04d}'


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    coffee_item = models.ForeignKey(Coffee, on_delete=models.SET_NULL, null=True, related_name='order_items')
    name = models.CharField(max_length=255)
    price = models.FloatField()
    quantity = models.PositiveIntegerField()

    def __str__(self):
        return f'{self.quantity} x {self.name}'

    @property
    def line_total(self):
        return self.price * self.quantity

# Biography models
class Biography(models.Model):
    name = models.CharField(max_length=255)
    gender = models.CharField(max_length=100)
    place_of_birth = models.CharField(max_length=255)
    date_birth = models.DateField()
    role = models.CharField(max_length=255)
    email = models.EmailField()
    mobile = models.CharField(max_length=20, validators=[phone_validator])
    hobby = models.CharField(max_length=255)
    language = models.CharField(max_length=255)

    def __str__(self):
        return self.name