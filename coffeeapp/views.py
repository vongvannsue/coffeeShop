from django.http import HttpResponse
from django.shortcuts import render
from .models import Coffee, Biography

# Create your views here.
def home(request):
    # return HttpResponse("Holle World!")
    coffee_list = Coffee.objects.all()
    return render(request, 'coffee.html', {'coffee':coffee_list})

def Biography_views(request):
    biography_list = Biography.objects.all()
    return render(request, 'biography.html', {'biography':biography_list})