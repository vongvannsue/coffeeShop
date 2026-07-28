from django.conf import settings
from django.core.validators import RegexValidator
from django.db import models

phone_validator = RegexValidator(
    regex=r'^\+?[0-9 ()-]{7,20}$',
    message="Enter a valid phone number (digits, spaces, '+', '-', '(', ')' only).",
)

# Coffee models
class Coffee(models.Model):
    name = models.CharField(max_length=255)
    price = models.FloatField()
    quantity = models.IntegerField()
    image = models.URLField()

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