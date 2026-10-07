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

# TURNOS
    path("pacientes/<str:dni>/turnos/", views.turno_lista, name="turno_lista"),
    path("pacientes/<str:dni>/turno/nuevo/", views.turno_crear, name="turno_crear"),
    path("pacientes/<str:dni>/turno/<int:turno_id>/editar/", views.turno_editar, name="turno_editar"),
    path("pacientes/<str:dni>/turno/<int:turno_id>/borrar/", views.turno_borrar, name="turno_borrar"),
    path("pacientes/<str:dni>/turno/<int:turno_id>/finalizar/", views.finalizar_turno, name="finalizar_turno"),

# AGENDA
    path("agenda/", views.agenda, name="agenda"),
    path("agenda/nuevo/", views.nuevo_turno_agenda, name="nuevo_turno_agenda"),
    path("agenda/turnos.json", views.turnos_json, name="turnos_json"),
    path("agenda/notas.json", views.agenda_notas, name="agenda_notas"),
    path("agenda/pacientes-disponibles.json", views.agenda_pacientes_disponibles_json, name="agenda_pacientes_disponibles_json"),
    path("agenda/asignar-disponible.json", views.agenda_asignar_turno_disponible, name="agenda_asignar_turno_disponible"),
    path("agenda/disponibilidad.json", views.agenda_disponibilidad_json, name="agenda_disponibilidad_json"),
    path("agenda/turnos/<int:turno_id>/estado/", views.agenda_turno_estado, name="agenda_turno_estado"),
    path("pacientes/<str:dni>/agendar/", views.agendar_turno, name="agendar_turno"),
    ]