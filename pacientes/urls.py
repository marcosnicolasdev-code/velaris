from django.urls import path
from . import views

urlpatterns = [
    path("pacientes/", views.paciente_lista, name="paciente_lista"),
    path("pacientes/nuevo/", views.paciente_crear, name="paciente_crear"),

    path("pacientes/<str:dni>/editar/", views.paciente_editar, name="paciente_editar"),
    path("pacientes/<str:dni>/borrar/", views.paciente_borrar, name="paciente_borrar"),
    path("pacientes/<str:dni>/evolucion/<int:evolucion_id>/", views.evolucion_detalle, name="evolucion_detalle"),
    path("pacientes/<str:dni>/", views.paciente_detalle, name="paciente_detalle"),
    path("pacientes/<str:dni>/agendar/", views.agendar_turno, name="agendar_turno",),
    path("pacientes/<str:dni>/evolucion/nueva/",views.evolucion_crear,name="evolucion_crear",),
    path("pacientes/<str:dni>/evolucion/profesional/nueva/", views.evolucion_profesional_crear, name="evolucion_profesional_crear"),

    path("pacientes/<str:dni>/turnos/", views.turno_lista, name="turno_lista"),
    path("pacientes/<str:dni>/turno/nuevo/", views.turno_crear, name="turno_crear"),
    path("pacientes/<str:dni>/turno/<int:turno_id>/editar/", views.turno_editar, name="turno_editar"),
    path("pacientes/<str:dni>/turno/<int:turno_id>/borrar/", views.turno_borrar, name="turno_borrar"),
    ]