from django.contrib.auth.decorators import login_required
from django.shortcuts import render

# Create your views here.


@login_required #solicita inciar sesion para avanzar en el sistema
def inicio(request):
    return render(request, 'inicio.html')


