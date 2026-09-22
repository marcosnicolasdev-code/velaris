from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Q
import unicodedata

from .models import Paciente
from .forms import PacienteForm

# READ  (El Listado y Buscador)
@login_required
def paciente_lista(request):
    q = request.GET.get("q", "").strip()
    pacientes = Paciente.objects.all()

    if q:
        busqueda = "".join(
            caracter
            for caracter in unicodedata.normalize("NFD", q.lower())
            if unicodedata.category(caracter) != "Mn"
        )

        pacientes = [
            paciente for paciente in pacientes
            if busqueda in unicodedata.normalize(
                "NFD", paciente.dni.lower()
            ).encode("ascii", "ignore").decode()
            or busqueda in unicodedata.normalize(
                "NFD", paciente.nombre_paciente.lower()
            ).encode("ascii", "ignore").decode()
            or busqueda in unicodedata.normalize(
                "NFD", paciente.apellido_paciente.lower()
            ).encode("ascii", "ignore").decode()
        ]

    return render(
        request,
        "pacientes/paciente_lista.html",
        {"pacientes": pacientes, "q": q},
    )


# READ muestra la información detallada de un solo paciente usando su DNI
@login_required
def paciente_detalle(request, dni):
    paciente = get_object_or_404(Paciente, dni=dni)
    return render(request, "pacientes/paciente_detalle.html", {"paciente": paciente})


# CREATE se usa el patrón GET/POST Sirve tanto para mostrar el formulario vacío como para guardar los datos cuando la recepcionista le da al botón "Guardar"
@login_required
def paciente_crear(request):
    if request.method == "POST":
        form = PacienteForm(request.POST)

        if form.is_valid():
            paciente = form.save()
            return redirect("paciente_detalle", dni=paciente.dni)
    else:
        form = PacienteForm()

    return render(
        request,
        "pacientes/paciente_form.html",
        {"form": form},
    )


# UPDATE  Es casi idéntico al de crear: usa instance=paciente para saber a quién estamos editando y precargar sus datos en los casilleros.
@login_required
def paciente_editar(request, dni):
    paciente = get_object_or_404(Paciente, dni=dni)
    if request.method == "POST":
        form = PacienteForm(request.POST, instance=paciente)
        if form.is_valid():
            form.save()
            return redirect("paciente_detalle", dni=paciente.dni)
    else:
        form = PacienteForm(instance=paciente)
    return render(request, "pacientes/paciente_form.html", {"form": form})


# DELETE
@login_required
def paciente_borrar(request, dni):
    paciente = get_object_or_404(Paciente, dni=dni)
    if request.method == "POST":
        paciente.delete()
        return redirect("paciente_lista")
    return render(request, "pacientes/paciente_confirmar.html", {"paciente": paciente})

#Agendar turno desde la lista de ptes.
@login_required
def agendar_turno(request, dni):
    paciente = get_object_or_404(Paciente, dni=dni)

    return render(
        request,
        "pacientes/agenda_provisoria.html",
        {"paciente": paciente},
    )