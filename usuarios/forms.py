from django import forms
from .models import Caja, Profesional


class CajaForm(forms.ModelForm):
    class Meta:
        model = Caja
        fields = ["usuario", "total_caja", "cierre_caja"]

class ProfesionalForm(forms.ModelForm):
    class Meta:
        model = Profesional
        fields = ["usuario", "matricula", "especialidad"]

