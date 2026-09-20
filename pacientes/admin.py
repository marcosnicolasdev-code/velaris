from django.contrib import admin
from .models import Paciente, HistoriaClinica, Turno, Evolucion, EvaluacionMedica

admin.site.register(Paciente)
admin.site.register(HistoriaClinica)
admin.site.register(Turno)


@admin.register(Evolucion)
class EvolucionAdmin(admin.ModelAdmin):
	exclude = ("resumen",)


admin.site.register(EvaluacionMedica)