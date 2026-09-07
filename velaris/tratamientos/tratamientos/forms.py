from django import forms 
from .models import Tratamiento
class TratamientoForm(forms.ModelForm):
    class Meta: 
        model = Tratamiento 
        fields = ["id_tratamiento","duracion_tratamiento","sesion_tratamiento"]
