from django import forms 
from .models import Tratamiento, PlanPago
class TratamientoForm(forms.ModelForm):
    class Meta: 
        model = Tratamiento 
        fields = ["id_tratamiento","duracion_tratamiento","sesion_tratamiento"]

class PlanPagoForm(forms.ModelForm):
    class Meta:
        model = PlanPago
        fields = ["id_plan","dni", "id_tratamiento","valor_sesion", "fecha_inicio_tratamiento"]

