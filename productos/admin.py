from django.contrib import admin
from .models import Producto, Venta, DetalleVenta, Archivo

admin.site.register(Producto)
admin.site.register(Venta)
admin.site.register(DetalleVenta)
admin.site.register(Archivo)
