from django.contrib import admin
from . models import coffee,biography

# coffee
class CoffeeAdmin(admin.ModelAdmin):
    list_display = ('name','price','quantity','image')
    search_fields = ('name',)

# biography
class BiographyAdmin(admin.ModelAdmin):
    list_display = ('name','gender','email','mobile','role','hobby','place_of_birth','language')
    search_fields = ('name',)

# Register your models here.
admin.site.register(coffee,CoffeeAdmin)
admin.site.register(biography,BiographyAdmin)