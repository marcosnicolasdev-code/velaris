from django.shortcuts import render


def pacientes(request):
    return render(request, 'pacientes.html')  # O el nombre del HTML que tengas preparado


# Create your views here.
