from django.shortcuts import render,redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Tratamiento 
from .forms import TratamientoForm 
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


# Create your views here.
