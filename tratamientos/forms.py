from django import forms 
from .models import Tratamiento, PlanPago, Sesion
class TratamientoForm(forms.ModelForm):
    class Meta: 
        model = Tratamiento 
        fields = ["nombre_tratamiento","duracion_tratamiento","sesion_tratamiento"]

class PlanPagoForm(forms.ModelForm):
    class Meta:
        model = PlanPago
        fields = ["nombre_tratamiento","valor_sesion", "fecha_inicio_tratamiento", 'metodo_pago']
    widgets = {
        'fecha_inicio_tratamiento':forms.DateInput(
         attrs ={'type':'date'}
        ),
    }
class SesionForm(forms.ModelForm):
    class Meta:
        model = Sesion
        fields = ["numero_sesion","duracion_sesion", 'estado_pago']
    widgets = {
        'fecha_sesion':forms.DateInput(
         attrs ={'type':'date'}
        ),
    }


