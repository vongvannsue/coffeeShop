from django.urls import path
from . import views

urlpatterns = [
    path('', views.home,name='home'),
    path('biography/', views.Biography_views,name='biography'),
    path('cart/', views.cart_detail, name='cart_detail'),
    path('cart/add/<int:coffee_id>/', views.add_to_cart, name='add_to_cart'),
    path('cart/remove/<int:coffee_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('cart/delete/<int:coffee_id>/', views.delete_from_cart, name='delete_from_cart'),
    path('cart/clear/', views.clear_cart, name='clear_cart'),
]