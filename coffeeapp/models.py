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