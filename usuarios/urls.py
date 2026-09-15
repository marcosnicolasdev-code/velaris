from django.urls import path
from . import views

urlpatterns = [
#URL de cajas
    path("cajas/", views.caja_lista, name="caja_lista"),
    path("cajas/<int:id>/editar/", views.caja_editar, name="caja_editar"),
    path("cajas/<int:id>/borrar/", views.caja_borrar, name="caja_borrar"),

#URL de movimientos de caja
    path("cajas/movimiento/nuevo/", views.registrar_movimiento, name="registrar_movimiento"),
    path("cajas/movimiento/", views.caja_movimientos, name="caja_movimientos"),

#URL de profesionales
    path("profesionales/", views.profesional_lista, name="profesional_lista"),
    path("profesionales/nuevo/", views.profesional_crear, name="profesional_crear"),
    path("profesionales/<int:id>/editar/", views.profesional_editar, name="profesional_editar"),
    path("profesionales/<int:id>/borrar/", views.profesional_borrar, name="profesional_borrar"),
]