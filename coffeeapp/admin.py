from datetime import timedelta

from django.contrib import admin
from django.core.exceptions import PermissionDenied
from django.db.models import Count, F, Sum
from django.db.models.functions import TruncDate
from django.template.response import TemplateResponse
from django.urls import path
from django.utils import timezone
from django.utils.html import format_html

from .models import Coffee, Biography, Order, OrderItem

RESTOCK_INCREMENT = 10
DASHBOARD_RANGES = ('today', 'week', 'month', 'all')

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


# Sales dashboard (MB-04) — gated on the custom coffeeapp.view_dashboard
# permission (Order.Meta.permissions), not a hardcoded group-name check,
# to stay consistent with how every other MB-0x issue gates access
# through real Permission objects. Registered by wrapping
# admin.site.get_urls() rather than a full AdminSite subclass, since this
# project registers models on the default admin.site everywhere else.
def dashboard_view(request):
    if not request.user.has_perm('coffeeapp.view_dashboard'):
        raise PermissionDenied

    range_key = request.GET.get('range', 'today')
    if range_key not in DASHBOARD_RANGES:
        range_key = 'today'

    completed = Order.objects.filter(status=Order.Status.COMPLETED)
    if range_key != 'all':
        now = timezone.now()
        since = {
            'today': now.replace(hour=0, minute=0, second=0, microsecond=0),
            'week': now - timedelta(days=7),
            'month': now - timedelta(days=30),
        }[range_key]
        completed = completed.filter(placed_at__gte=since)

    totals = completed.aggregate(total_sales=Sum('total'), order_count=Count('id'))

    best_sellers = (
        OrderItem.objects.filter(order__in=completed)
        .values('name')
        .annotate(units=Sum('quantity'))
        .order_by('-units')[:10]
    )

    revenue_by_day = (
        completed.annotate(day=TruncDate('placed_at'))
        .values('day')
        .annotate(revenue=Sum('total'))
        .order_by('day')
    )

    context = {
        **admin.site.each_context(request),
        'title': 'Sales Dashboard',
        'range_key': range_key,
        'ranges': DASHBOARD_RANGES,
        'total_sales': totals['total_sales'] or 0,
        'order_count': totals['order_count'] or 0,
        'best_sellers': best_sellers,
        'revenue_by_day': revenue_by_day,
    }
    return TemplateResponse(request, 'admin/coffeeapp/dashboard.html', context)


_wrapped_get_urls = admin.site.get_urls


def _get_urls_with_dashboard():
    return [
        path('dashboard/', admin.site.admin_view(dashboard_view), name='dashboard'),
    ] + _wrapped_get_urls()


admin.site.get_urls = _get_urls_with_dashboard