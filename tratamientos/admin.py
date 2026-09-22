from django.contrib import admin
# Register your models here.
from .models import Tratamiento, PlanPago ,Sesion, Receta
# Register your models here.
admin.site.register(Tratamiento)
admin.site.register(PlanPago)
admin.site.register(Sesion)
admin.site.register(Receta)
