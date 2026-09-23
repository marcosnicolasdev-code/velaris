from django.urls import path
from . import views

urlpatterns = [
    path("", views.producto_lista, name="producto_lista"),
    path("productos/nuevo/", views.producto_crear, name="producto_crear"),
    path("productos/<str:codigo>/editar/", views.producto_editar, name="producto_editar"),
    path("productos/<str:codigo>/borrar/", views.producto_borrar, name="producto_borrar"),
]