from django.urls import path
from . import views

urlpatterns = [
    path('', views.home,name='home'),
    path('biography/', views.Biography_views,name='biography'),
]