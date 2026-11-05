from django.contrib.auth.decorators import login_required
from django.shortcuts import render , redirect , get_object_or_404
from .models import Caja, Profesional, MovimientoCaja
from .forms import CajaForm, ProfesionalForm, MovimientoCajaForm
from django.utils import timezone
from django.db.models import Sum

from pacientes.models import Turno
from .permissions import exigir_acceso_secciones_administrativas

# Create your views here.


@login_required #solicita inciar sesion para avanzar en el sistema
def inicio(request):
    hoy = timezone.localdate()
    turnos_hoy = Turno.objects.filter(fecha_asistencia__date=hoy).exclude(estado=Turno.Estado.CANCELADO)

    turnos_pendientes = turnos_hoy.exclude(
        estado__in=[Turno.Estado.FINALIZADO, Turno.Estado.CANCELADO, Turno.Estado.AUSENTE]
    ).count()
    pacientes_en_espera = turnos_hoy.filter(
        estado__in=[Turno.Estado.RESERVADO, Turno.Estado.ASIGNADO]
    ).count()

    turnos = (
        turnos_hoy.select_related("paciente", "tratamiento")
        .order_by("fecha_asistencia")
    )

    sala_espera = []
    for turno in turnos:
        profesional = "Sin asignar"
        evolucion = turno.evoluciones.order_by("-id").first()
        if evolucion and evolucion.profesional:
            profesional = evolucion.profesional.usuario.get_full_name() or evolucion.profesional.usuario.username

        estado_label = {
            Turno.Estado.RESERVADO: "En espera",
            Turno.Estado.ASIGNADO: "En espera",
            Turno.Estado.PRESENTE: "En consultorio",
            Turno.Estado.FINALIZADO: "Finalizado",
            Turno.Estado.CANCELADO: "Cancelado",
            Turno.Estado.AUSENTE: "Cancelado",
        }.get(turno.estado, turno.get_estado_display())

        sala_espera.append({
            "turno": turno,
            "profesional": profesional,
            "estado_label": estado_label,
        })

    return render(request, 'inicio.html', {
        "sala_espera": sala_espera,
        "pacientes_del_dia": turnos_hoy.count(),
        "turnos_pendientes": turnos_pendientes,
        "en_espera": pacientes_en_espera,
    })


#CRUD Caja - El orden se rige por lo que va necesitando el sistema paso a paso

#READ - listar todas las cajas
@login_required
def caja_lista(request):
    exigir_acceso_secciones_administrativas(request.user)
    cajas = Caja.objects.all() #Trae todas las cajas (ORM)
    return render (request, "usuarios/caja_lista.html", {"cajas": cajas})

#CREATE - crear una caja nueva no tiene formulario para evitar duplicados de cajas

#UPDATE - editar una caja existente
@login_required
def caja_editar(request, id):
    exigir_acceso_secciones_administrativas(request.user)
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
    exigir_acceso_secciones_administrativas(request.user)
    caja = get_object_or_404(Caja, id=id)
    if request.method == "POST":
        caja.delete()
        return redirect("caja_lista")
    return render(request, "usuarios/caja_confirmar.html", {"caja": caja})

#CRUD Movimiento de Caja

# CREATE - Registrar un movimiento de caja (ingreso o egreso)
@login_required
def registrar_movimiento(request):
    exigir_acceso_secciones_administrativas(request.user)
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
    exigir_acceso_secciones_administrativas(request.user)
    # Si viene un id, es esa caja; si no, la del usuario logueado
    if id:
        caja = get_object_or_404(Caja, id=id)
        es_propia = (caja.usuario == request.user)
    else:
        caja = get_object_or_404(Caja, usuario=request.user)
        es_propia = True

    hoy = timezone.localdate()
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
    exigir_acceso_secciones_administrativas(request.user)
    caja = get_object_or_404(Caja, id=id)
    hoy = timezone.localdate()

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
    exigir_acceso_secciones_administrativas(request.user)
    profesionales = Profesional.objects.all()
    return render(request, "usuarios/profesional_lista.html", {"profesionales": profesionales})

#CREATE - crear un profesional nuevo
@login_required
def profesional_crear(request):
    exigir_acceso_secciones_administrativas(request.user)
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
    exigir_acceso_secciones_administrativas(request.user)
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
    exigir_acceso_secciones_administrativas(request.user)
    profesional = get_object_or_404(Profesional, id=id)
    if request.method == "POST":
        profesional.delete()
        return redirect("profesional_lista")
    return render(request, "usuarios/profesional_confirmar.html", {"profesional": profesional})
