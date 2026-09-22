from django.contrib import admin
from .models import Paciente, HistoriaClinica, Turno, EvaluacionMedica

admin.site.register(Paciente)
admin.site.register(HistoriaClinica)
admin.site.register(Turno)
admin.site.register(EvaluacionMedica)