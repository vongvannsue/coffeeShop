from django.contrib import admin
from .models import Coffee, Biography, Order, OrderItem

# coffee
class CoffeeAdmin(admin.ModelAdmin):
    list_display = ('name','category','price','quantity','image')
    list_filter = ('category',)
    search_fields = ('name',)

# biography
class BiographyAdmin(admin.ModelAdmin):
    list_display = ('name','gender','email','mobile','role','hobby','place_of_birth','language')
    search_fields = ('name',)

# orders
class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('coffee_item', 'name', 'price', 'quantity')
    can_delete = False

class OrderAdmin(admin.ModelAdmin):
    list_display = ('display_number', 'user', 'placed_at', 'total')
    list_filter = ('placed_at',)
    search_fields = ('user__username',)
    readonly_fields = ('user', 'placed_at', 'subtotal', 'tax', 'total')
    inlines = [OrderItemInline]

# Register your models here.
admin.site.register(Coffee, CoffeeAdmin)
admin.site.register(Biography, BiographyAdmin)
admin.site.register(Order, OrderAdmin)