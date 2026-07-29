from django.contrib import admin
from django.db.models import F
from django.utils.html import format_html

from .models import Coffee, Biography, Order, OrderItem

RESTOCK_INCREMENT = 10

STATUS_COLORS = {
    Order.Status.PENDING: '#6c757d',
    Order.Status.PREPARING: '#fd7e14',
    Order.Status.READY: '#0d6efd',
    Order.Status.COMPLETED: '#198754',
    Order.Status.CANCELLED: '#dc3545',
}

# coffee
class CoffeeAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'price', 'stock_badge', 'image')
    list_filter = ('category',)
    search_fields = ('name',)
    actions = ['restock']

    @admin.display(description='Stock', ordering='quantity')
    def stock_badge(self, obj):
        low = obj.quantity <= obj.low_stock_threshold
        color = '#dc3545' if low else '#198754'
        label = f'{obj.quantity} (LOW)' if low else str(obj.quantity)
        return format_html(
            '<span style="background-color:{}; color:#fff; padding:2px 8px; '
            'border-radius:4px; font-size:12px;">{}</span>',
            color, label,
        )

    @admin.action(description=f'Restock selected (+{RESTOCK_INCREMENT})')
    def restock(self, request, queryset):
        updated = queryset.update(quantity=F('quantity') + RESTOCK_INCREMENT)
        self.message_user(request, f'Restocked {updated} item(s) by +{RESTOCK_INCREMENT}.')

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
    list_display = ('display_number', 'user', 'placed_at', 'total', 'status_badge')
    list_filter = ('status', 'placed_at')
    search_fields = ('user__username',)
    readonly_fields = ('user', 'placed_at', 'subtotal', 'tax', 'total')
    inlines = [OrderItemInline]
    actions = ['mark_preparing', 'mark_ready', 'mark_completed', 'mark_cancelled']

    @admin.display(description='Status')
    def status_badge(self, obj):
        color = STATUS_COLORS.get(obj.status, '#6c757d')
        return format_html(
            '<span style="background-color:{}; color:#fff; padding:2px 8px; '
            'border-radius:4px; font-size:12px;">{}</span>',
            color, obj.get_status_display(),
        )

    def _mark(self, request, queryset, status, label):
        updated = queryset.update(status=status)
        self.message_user(request, f'{updated} order(s) marked as {label}.')

    @admin.action(description='Mark selected orders as Preparing')
    def mark_preparing(self, request, queryset):
        self._mark(request, queryset, Order.Status.PREPARING, 'Preparing')

    @admin.action(description='Mark selected orders as Ready')
    def mark_ready(self, request, queryset):
        self._mark(request, queryset, Order.Status.READY, 'Ready')

    @admin.action(description='Mark selected orders as Completed')
    def mark_completed(self, request, queryset):
        self._mark(request, queryset, Order.Status.COMPLETED, 'Completed')

    @admin.action(description='Mark selected orders as Cancelled')
    def mark_cancelled(self, request, queryset):
        self._mark(request, queryset, Order.Status.CANCELLED, 'Cancelled')

# Register your models here.
admin.site.register(Coffee, CoffeeAdmin)
admin.site.register(Biography, BiographyAdmin)
admin.site.register(Order, OrderAdmin)