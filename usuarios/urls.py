from django.urls import path
from . import views

urlpatterns = [
    path("cajas/", views.caja_lista, name="caja_lista"),
    path("cajas/nueva", views.caja_crear, name="caja_crear"),
    path("cajas/<int:id>/editar/", views.caja_editar, name="caja_editar"),
    path("cajas/<int:id>/borrar/", views.caja_borrar, name="caja_borrar"),
]