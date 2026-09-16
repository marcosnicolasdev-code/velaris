from django import forms
from .models import Paciente

class PacienteForm(forms.ModelForm):
    class Meta:
        model = Paciente
        fields = [
            "dni", "nombre_paciente", "apellido_paciente", "fecha_nacimiento",
            "domicilio", "localidad", "correo_electronico", "telefono",
            "obra_social", "sexo",
        ]
