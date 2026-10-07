from django import forms 
from pacientes.models import Evolucion
from .models import Tratamiento, PlanPago, Sesion
class TratamientoForm(forms.ModelForm):
    class Meta: 
        model = Tratamiento 
        fields = ["nombre_tratamiento","duracion_tratamiento","sesion_tratamiento"]

class PlanPagoForm(forms.ModelForm):
    class Meta:
        model = PlanPago
        fields = ["dni", "tratamiento", "metodo_pago"]

    def __init__(self, *args, paciente=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.paciente = paciente
        self.fields["tratamiento"].queryset = Tratamiento.objects.filter(requiere_plan=True)
        if paciente:
            self.fields.pop("dni")
            indicados = Evolucion.objects.filter(
                historia_clinica__paciente=paciente,
                tratamiento_indicado__isnull=False,
            ).values_list("tratamiento_indicado_id", flat=True)
            self.fields["tratamiento"].queryset = self.fields["tratamiento"].queryset.filter(
                pk__in=indicados
            ).exclude(
                pk__in=PlanPago.objects.filter(
                    dni=paciente,
                    estado="activo",
                ).values_list("tratamiento_id", flat=True)
            )

    def clean(self):
        cleaned = super().clean()
        paciente = self.paciente or cleaned.get("dni")
        tratamiento = cleaned.get("tratamiento")
        if paciente and tratamiento and not Evolucion.objects.filter(
            historia_clinica__paciente=paciente,
            tratamiento_indicado=tratamiento,
        ).exists():
            self.add_error("tratamiento", "El tratamiento debe estar indicado por un médico.")
        return cleaned

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
