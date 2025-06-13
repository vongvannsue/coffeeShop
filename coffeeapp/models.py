from django.db import models

# Create your models here.

# Coffee models
class coffee(models.Model):
    name = models.CharField(max_length=255)
    price = models.FloatField()
    quantity = models.IntegerField()
    image = models.CharField(max_length=2083)

# Biography models
class biography(models.Model):
    name = models.CharField(max_length=255)
    gender = models.CharField(max_length=100)
    place_of_birth = models.CharField(max_length=255)
    data_birth = models.DateTimeField()
    role =models.CharField(max_length=255)
    email = models.EmailField()
    mobile = models.IntegerField()
    hobby = models.CharField(max_length=255)
    language = models.CharField(max_length=255)