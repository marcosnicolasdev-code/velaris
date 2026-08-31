from django.contrib.auth.decorators import login_required
from django.shortcuts import render , redirect , get_object_or_404
from .models import Caja
from .forms import CajaForm

# Create your views here.


@login_required #solicita inciar sesion para avanzar en el sistema
def inicio(request):
    return render(request, 'inicio.html')


#CRUD Caja - El orden se rige por lo que va necesitando el sistema paso a paso

#READ - listar todas las cajas
@login_required
def caja_lista(request):
    cajas = Caja.objects.all() #Trae todas las cajas (ORM)
    return render (request, "usuarios/caja_lista.html", {"cajas": cajas})

#CREATE - crea una caja nueva
@login_required
def caja_crear(request):
    if request.method == "POST": # Pregunta si es POST 
        form = CajaForm (request.POST) # Lee los datos que se cargaron
        if form.is_valid():
            form.save()
            return redirect("caja_lista")
    else:
        form = CajaForm() # Entro en el if y reconocio que no es POST, por descarte es GET
    return render (request, "usuarios/caja_form.html", {"form": form})

#UPDATE - editar una caja existente
@login_required
def caja_editar(request, id):
    caja = get_object_or_404(Caja, id=id)
    if request.method == "POST":
        form = CajaForm (request.POST, instance=caja) # Solicita que empiece con los datos de esa caja
        if form.is_valid():
            form.save()
            return redirect("caja_lista")
    else:
        form = CajaForm(instance=caja)
    return render (request, "usuarios/caja_form.html", {"form": form})

#DELETE - borrar una caja
@login_required
def caja_borrar(request, id):
    caja = get_object_or_404(Caja, id=id)
    if request.method == "POST":
        caja.delete()
        return redirect("caja_lista")
    return render(request, "usuarios/caja_confirmar.html", {"caja": caja})


