from django.contrib.auth.decorators import login_required
from django.shortcuts import render , redirect , get_object_or_404
from .models import Caja, Profesional, MovimientoCaja
from .forms import CajaForm, ProfesionalForm, MovimientoCajaForm
from django.utils import timezone
from django.db.models import Sum

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

#CREATE - crear una caja nueva no tiene formulario para evitar duplicados de cajas

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

#CRUD Movimiento de Caja

# CREATE - Registrar un movimiento de caja (ingreso o egreso)
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
            return redirect("caja_movimientos")
    else:
        form = MovimientoCajaForm()

    return render(request, "usuarios/movimiento_form.html", {"form": form})

# READ - Listar todos los movimientos de caja del usuario

@login_required
def caja_movimientos(request, id=None):
    # Si viene un id, es esa caja; si no, la del usuario logueado
    if id:
        caja = get_object_or_404(Caja, id=id)
        es_propia = (caja.usuario == request.user)
    else:
        caja = get_object_or_404(Caja, usuario=request.user)
        es_propia = True

    hoy = timezone.now().date()
    # Solo los movimientos de hoy de esta caja
    movimientos = MovimientoCaja.objects.filter(
        caja=caja, 
        fecha_movimiento__date=hoy
    ).order_by("-fecha_movimiento") # El signo - indica que se ordena de forma descendente, se mostrara el ultimo movimiento primero

    # Totales del dia
    ingresos = movimientos.filter(tipo_movimiento="ingreso").aggregate( # aggregate suma todos los movimientos de ese tipo
        total=Sum("importe_movimiento"))["total"] or 0
    egresos = movimientos.filter(tipo_movimiento="egreso").aggregate(
        total=Sum("importe_movimiento"))["total"] or 0
    saldo = ingresos - egresos

    return render(request, "usuarios/caja_movimientos.html", {
        "caja": caja,
        "movimientos": movimientos,
        "ingresos": ingresos,
        "egresos": egresos,
        "saldo": saldo,
        "es_propia": es_propia,
    })


# READ - Listar todos los movimientos de caja para visualizacion de CEO/ADMINISTRADOR

@login_required
def caja_detalle(request, id):
    caja = get_object_or_404(Caja, id=id)
    hoy = timezone.now().date()

    movimientos = MovimientoCaja.objects.filter(
        caja=caja,
        fecha_movimiento__date=hoy
    ).order_by("-fecha_movimiento")

    # Totales de la caja
    ingresos = movimientos.filter(tipo_movimiento="ingreso").aggregate(
        total=Sum("importe_movimiento"))["total"] or 0
    egresos = movimientos.filter(tipo_movimiento="egreso").aggregate(
        total=Sum("importe_movimiento"))["total"] or 0
    saldo = ingresos - egresos

    return render(request, "usuarios/caja_detalle.html", {
        "caja": caja,
        "movimientos": movimientos,
        "ingresos": ingresos,
        "egresos": egresos,
        "saldo": saldo,
    })

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

