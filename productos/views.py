from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Producto
from .forms import ProductoForm


@login_required
def producto_lista(request):
    productos = Producto.objects.all()
    return render(request, "productos/producto_lista.html", {"productos": productos})


@login_required
def producto_crear(request):
    if request.method == "POST": 
        form = ProductoForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("producto_lista")
        
    else:
        form = ProductoForm()
        
    return render(request, "productos/producto_form.html", {"form": form})
        

@login_required
def producto_editar(request, codigo):
    producto = get_object_or_404(Producto, codigo_producto=codigo)
    if request.method == "POST":
        form = ProductoForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("producto_lista")
        else:
            form = ProductoForm()
        return render(request, "productos/producto_form.html", {"form": form})
    
@login_required
def producto_editar(request, codigo):
    producto = get_object_or_404(Producto, codigo_producto=codigo)
    if request.method == "POST":
        form = ProductoForm(request.POST, instance=producto)
        if form.is_valid():
            form.save()
        return redirect("producto_lista")
    else:
        form = ProductoForm(instance=producto)
        return render(request, "productos/producto_form.html", {"form": form})
    
@login_required
def producto_borrar(request, codigo):
    producto = get_object_or_404(Producto, codigo_producto=codigo)
    if request.method == "POST":
        producto.delete()
        return redirect("producto_lista")
    return render(request, "productos/producto_confirmar.html", {"producto": producto})
    
        