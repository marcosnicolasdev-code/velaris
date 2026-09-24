from django import forms 
from .models import Tratamiento, PlanPago, Sesion
class TratamientoForm(forms.ModelForm):
    class Meta: 
        model = Tratamiento 
        fields = ["nombre_tratamiento","duracion_tratamiento","sesion_tratamiento"]

class PlanPagoForm(forms.ModelForm):
    class Meta:
        model = PlanPago
        fields = ["tratamiento","valor_sesion", 'metodo_pago']

class SesionForm(forms.ModelForm):
    class Meta:
        model = Sesion
        fields = ["numero_sesion","duracion_sesion", 'estado_pago']


class AsignarPlanForm(forms.ModelForm):
    class Meta:
        model = PlanPago
        fields = ["tratamiento", "metodo_pago"]

    def __init__(self, *args, **kwargs):
        super(). __init__(*args, **kwargs)
        # Solo se muestran tratamientos que requieren plan (NTF, PRP, MTC)
        self.fields["tratamiento"].queryset = Tratamiento.objects.filter(requiere_plan=True)
