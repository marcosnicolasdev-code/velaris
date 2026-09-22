from django.urls import path
from . import views

urlpatterns = [
    path("pacientes/", views.paciente_lista, name="paciente_lista"),
    path("pacientes/nuevo/", views.paciente_crear, name="paciente_crear"),

    path("pacientes/<str:dni>/editar/", views.paciente_editar, name="paciente_editar"),
    path("pacientes/<str:dni>/borrar/", views.paciente_borrar, name="paciente_borrar"),
    path("pacientes/<str:dni>/", views.paciente_detalle, name="paciente_detalle"),
    path("pacientes/<str:dni>/agendar/", views.agendar_turno, name="agendar_turno",),
    ]