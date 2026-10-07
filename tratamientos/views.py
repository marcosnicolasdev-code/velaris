from django.shortcuts import render,redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.utils import timezone
from pacientes.models import Paciente, Turno
from .models import Tratamiento, PlanPago
from .forms import TratamientoForm, AsignarPlanForm, SesionForm, PlanPagoForm
import unicodedata

@login_required 
def tratamiento_lista (request): 
    tratamientos = Tratamiento.objects.all()
    return render (request,"tratamientos/tratamiento_lista.html", {"tratamientos": tratamientos})
@login_required 
def tratamiento_crear(request): 
    if request.method == "POST": 
        form = TratamientoForm(request.POST)
        if form.is_valid(): 
            form.save()
        return redirect("tratamiento_lista")
    else:
        form = TratamientoForm()
        return render(request,"tratamientos/tratamiento_form.html", {"form":form})
@login_required
def tratamiento_editar(request,id):
    tratamiento = get_object_or_404(Tratamiento,id_tratamiento=id)
    if request.method == "POST":
        form = TratamientoForm (request.POST,instance=tratamiento)
        if form.is_valid():
            form.save()
        return redirect("tratamiento_lista")
    else:
        form = TratamientoForm(instance=tratamiento)
        return render(request,"tratamientos/tratamiento_form.html",{"form": form})
@login_required
def tratamiento_borrar(request,id):
    tratamiento = get_object_or_404(Tratamiento,id_tratamiento=id)
    if request.method =="POST":
        tratamiento.delete()
        return redirect("tratamiento_lista")
    return render(request,"tratamientos/tratamiento_confirmar.html",{"tratamiento": tratamiento})

# --------PLAN PAGO -------------
@login_required 
def planpago_lista (request): 
    planes = PlanPago.objects.select_related('nombre_tratamiento').all()
    return render (request,"tratamientos/planpago_lista.html", {"planes": planes})
@login_required 
def planpago_crear(request, dni=None):
    grupos = {
        unicodedata.normalize("NFKD", nombre or "")
        .encode("ascii", "ignore")
        .decode("ascii")
        .strip()
        .lower()
        for nombre in request.user.groups.values_list("name", flat=True)
    }
    if not request.user.is_superuser and not (grupos & {"recepcionista", "ceo"}):
        raise PermissionDenied
    paciente = get_object_or_404(Paciente, dni=dni) if dni else None
    if request.method == 'POST': 
        form = PlanPagoForm(request.POST, paciente=paciente)
        if form.is_valid(): 
            plan = form.save(commit=False)
            if paciente:
                plan.dni = paciente
            if PlanPago.objects.filter(dni=plan.dni, tratamiento=plan.tratamiento, estado="activo").exists():
                form.add_error("tratamiento", "El paciente ya tiene un plan activo para este tratamiento.")
            else:
                with transaction.atomic():
                    plan.sesiones_total = plan.tratamiento.sesion_tratamiento
                    plan.valor_sesion = plan.tratamiento.precio_por_sesion
                    plan.save()
                    ahora = timezone.now()
                    Turno.objects.filter(
                        paciente=plan.dni,
                        tratamiento=plan.tratamiento,
                        fecha_asistencia__gte=ahora,
                        plan__isnull=True,
                        estado__in=["reservado", "asignado"],
                        indicacion_medica__tratamiento_indicado=plan.tratamiento,
                    ).update(plan=plan)
                return redirect("paciente_detalle", dni=plan.dni_id) if paciente else redirect("planpago_lista")
    else:
        form = PlanPagoForm(paciente=paciente)
    return render(
        request,
        "tratamientos/planpago_form.html",
        {"form": form, "paciente": paciente},
    )
@login_required
def planpago_editar(request,id):
    planes = get_object_or_404(PlanPago,id_plan=id)
    if request.method == "POST":
        form = PlanPagoForm (request.POST,instance=planes)
        if form.is_valid():
         form.save()
         return redirect("planpago_lista")
    else:
        form = PlanPagoForm(instance=planes)
    return render(request,"tratamientos/planpago_form.html",{"form": form})
@login_required
def planpago_borrar(request,id):
    planes = get_object_or_404(PlanPago,id_plan=id)
    if request.method =="POST":
        planes.delete()
        return redirect("planpago_lista")
    return render(request,"tratamientos/planpago_confirmar_borrar.html",{"planes": planes})

# ---------Sesion ----------------
@login_required 
def sesion_lista (request): 
    sesiones = Sesion.objects.all()
    return render (request,"tratamientos/sesion_lista.html", {"sesiones": sesiones})

@login_required 
def sesion_crear(request): 
    if request.method == 'POST': 
        form = SesionForm(request.POST)
        if form.is_valid(): 
         form.save()
         return redirect("sesion_lista")
    else:
        form = SesionForm()
    return render(request,"tratamientos/sesion_form.html", {"form":form})
@login_required
def sesion_editar(request,id_sesion):
    sesion = get_object_or_404(Sesion, id_sesion=id_sesion)
    if request.method == "POST":
        form = SesionForm (request.POST,instance=sesion)
        if form.is_valid():
         form.save()
         return redirect("sesion_lista")
    else:
        form = SesionForm(instance=sesion)
    return render(request,"tratamientos/sesion_form.html",{"form": form})
@login_required
def sesion_borrar(request,id_sesion):
    sesion = get_object_or_404(Sesion, id_sesion=id_sesion)
    if request.method =="POST":
        sesion.delete()
        return redirect("sesion_lista")
    return render(request,"tratamientos/sesion_confirmar_borrar.html",{"sesion": sesion})


# ASIGNACION DE TRATAMIENTOS POR PARTE DEL MEDICO
@login_required
def asignar_plan(request, dni):
    return redirect("evolucion_profesional_crear", dni=dni)
    