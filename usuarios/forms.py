from django import forms
from .models import Caja, Profesional, MovimientoCaja


class CajaForm(forms.ModelForm):
    class Meta:
        model = Caja
        fields = ["usuario", "total_caja", "cierre_caja"]

class ProfesionalForm(forms.ModelForm):
    class Meta:
        model = Profesional
        fields = ["usuario", "matricula", "especialidad"]

class MovimientoCajaForm(forms.ModelForm):
    class Meta:
        model = MovimientoCaja
        fields = ["tipo_movimiento","categoria_movimiento", "descripcion_movimiento", "importe_movimiento"] # La caja y la fecha se omiten porque el sistema las asigna de forma automática.
        widgets = {
            "descripcion_movimiento": forms.Textarea(attrs={"rows": 3, "max_length": 200, "style": "display: block; max-width: 500px; height: 100px; width: 100%; resize: none", "placeholder": "Ingrese una descripción del movimiento (opcional)"}),
        }