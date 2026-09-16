from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Paciente
from .forms import PacienteForm


# READ 
@login_required
def paciente_lista(request):
    q = request.GET.get("q", "")
    if q:
        pacientes = Paciente.objects.filter(apellido_paciente__icontains=q)
    else:
        pacientes = Paciente.objects.all()
    return render(request, "pacientes/paciente_lista.html", {"pacientes": pacientes, "q": q})


# READ 
@login_required
def paciente_detalle(request, dni):
    paciente = get_object_or_404(Paciente, dni=dni)
    return render(request, "pacientes/paciente_detalle.html", {"paciente": paciente})


# CREATE
@login_required
def paciente_crear(request):
    if request.method == "POST":
        form = PacienteForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("paciente_lista")
    else:
        form = PacienteForm()
    return render(request, "pacientes/paciente_form.html", {"form": form})


# UPDATE
@login_required
def paciente_editar(request, dni):
    paciente = get_object_or_404(Paciente, dni=dni)
    if request.method == "POST":
        form = PacienteForm(request.POST, instance=paciente)
        if form.is_valid():
            form.save()
            return redirect("paciente_lista")
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