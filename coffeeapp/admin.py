from django.contrib import admin
from .models import Coffee, Biography

# coffee
class CoffeeAdmin(admin.ModelAdmin):
    list_display = ('name','price','quantity','image')
    search_fields = ('name',)

# biography
class BiographyAdmin(admin.ModelAdmin):
    list_display = ('name','gender','email','mobile','role','hobby','place_of_birth','language')
    search_fields = ('name',)

# Register your models here.
admin.site.register(Coffee, CoffeeAdmin)
admin.site.register(Biography, BiographyAdmin)