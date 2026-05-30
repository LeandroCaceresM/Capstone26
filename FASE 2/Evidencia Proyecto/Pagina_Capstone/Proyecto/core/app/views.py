from django.http import HttpResponse
from django.shortcuts import render

def tulon(request):
    return render(request, 'tulon.html')