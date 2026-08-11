from django.contrib import admin
from .models import Tratamiento, PlanPago, Sesion, Receta

admin.site.register(Tratamiento)
admin.site.register(PlanPago)
admin.site.register(Sesion)
admin.site.register(Receta)

