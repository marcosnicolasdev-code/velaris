from django.contrib.auth.decorators import login_required
from django.shortcuts import render , redirect , get_object_or_404
from .models import Caja, Profesional, MovimientoCaja
from .forms import CajaForm, ProfesionalForm, MovimientoCajaForm

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


# Registrar un movimiento de caja (ingreso o egreso)
@login_required
def registrar_movimiento(request):
    # Busca la caja del usuario actualmente logueado (request.user)
    caja = get_object_or_404(Caja, usuario=request.user)

    if request.method == "POST":
        form = MovimientoCajaForm(request.POST)
        if form.is_valid():
            movimiento = form.save(commit=False)
            movimiento.caja = caja
            movimiento.save()
            return redirect("caja_lista")
    else:
            form = MovimientoCajaForm()

    return render(request, "usuarios/movimiento_form.html", {"form": form})

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

#CRUD Profesional

#READ - listar todos los profesionales
@login_required
def profesional_lista(request):
    profesionales = Profesional.objects.all()
    return render(request, "usuarios/profesional_lista.html", {"profesionales": profesionales})

#CREATE - crear un profesional nuevo
@login_required
def profesional_crear(request):
    if request.method == "POST":
        form = ProfesionalForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("profesional_lista")
    else:
        form = ProfesionalForm()
    return render(request, "usuarios/profesional_form.html", {"form": form})

#UPDATE - editar un profesional existente
@login_required
def profesional_editar(request, id):
    profesional = get_object_or_404(Profesional, id=id)
    if request.method == "POST":
        form = ProfesionalForm(request.POST, instance=profesional)
        if form.is_valid():
            form.save()
            return redirect("profesional_lista")
    else:
        form = ProfesionalForm(instance=profesional)
    return render(request, "usuarios/profesional_form.html", {"form": form})

#DELETE - borrar un profesional
@login_required
def profesional_borrar(request, id):
    profesional = get_object_or_404(Profesional, id=id)
    if request.method == "POST":
        profesional.delete()
        return redirect("profesional_lista")
    return render(request, "usuarios/profesional_confirmar.html", {"profesional": profesional})

