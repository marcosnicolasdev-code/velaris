from django import forms
from .models import Paciente

class PacienteForm(forms.ModelForm):

    OPCIONES_SEXO = [
        ("", "Seleccionar..."),
        ("Varón", "Varón"),
        ("Mujer", "Mujer"),
    ]

    sexo = forms.ChoiceField(
        choices=OPCIONES_SEXO,
        required=False,
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for campo in self.fields.values():
            campo.error_messages["required"] = "Este campo es obligatorio."
            campo.error_messages["invalid"] = "Ingresá un valor válido."

        self.fields["dni"].error_messages["unique"] = (
            "Ya existe un paciente registrado con este DNI."
        )

    class Meta:
        model = Paciente

        fields = [
            "dni",
            "nombre_paciente",
            "apellido_paciente",
            "fecha_nacimiento",
            "domicilio",
            "localidad",
            "correo_electronico",
            "telefono",
            "obra_social",
            "sexo",
        ]
        
        widgets = {
            "dni": forms.TextInput(attrs={"class": "form-control", "placeholder": "Ej: 42345678"}),
            "nombre_paciente": forms.TextInput(attrs={"class": "form-control", "placeholder": "Nombre/s"}),
            "apellido_paciente": forms.TextInput(attrs={"class": "form-control", "placeholder": "Apellido/s"}),
            "fecha_nacimiento": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "domicilio": forms.TextInput(attrs={"class": "form-control", "placeholder": "Calle y número"}),
            "localidad": forms.TextInput(attrs={"class": "form-control", "placeholder": "Ciudad"}),
            "correo_electronico": forms.EmailInput(attrs={"class": "form-control", "placeholder": "ejemplo@correo.com"}),
            "telefono": forms.TextInput(attrs={"class": "form-control", "placeholder": "Ej: 3416123456"}),
            "obra_social": forms.TextInput(attrs={"class": "form-control", "placeholder": "Nombre de cobertura"}),
        }
