from django.urls import path
from . import views

urlpatterns = [
    path("", views.tratamiento_lista, name= "tratamiento_lista"), 
    path("nuevo/", views.tratamiento_crear, name="tratamiento_crear"), 
    path("<str:id>/editar", views.tratamiento_editar, name="tratamiento_editar"), 
    path("<str:id>/borrar", views.tratamiento_borrar, name= "tratamiento_borrar"),

# --------PLAN PAGO--------------
path("", views.planpago_lista, name="planpago_lista"),
path("nuevo/", views.planpago_crear, name="planpago_crear"),
path("<str:id>/editar", views.planpago_editar, name="planpago_editar"),
path("<str:id>/borrar", views.planpago_borrar, name="planpago_borrar"),
]