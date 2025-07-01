from django.http import HttpResponse
from django.shortcuts import render
from .models import coffee,biography

# Create your views here.
def home(request):
    # return HttpResponse("Holle World!")
    Coffee = coffee.objects.all()
    return render(request, 'coffee.html', {'coffee':Coffee})

def Biography_views(request):
    Biography = biography.objects.all()
    return render(request, 'biography.html', {'biography':Biography})