from datetime import datetime, timedelta

from django import forms
from django.db.models import F
from django.utils import timezone
from .models import Evolucion, Paciente, Turno 
from tratamientos.models import Tratamiento, PlanPago

class PacienteForm(forms.ModelForm):

    OPCIONES_SEXO = [
        ("", "Seleccionar..."),
        ("Masculino", "Masculino"),
        ("Femenino", "Femenino"),
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

class TurnoForm(forms.ModelForm):
    class Meta:
        model = Turno
        fields = ["tratamiento", "fecha_asistencia", "estado"]
        widgets = {
            "fecha_asistencia": forms.DateInput(attrs={"class": "form-control", "type": "datetime-local"}),
        }

class AgendarTurnoForm(forms.ModelForm):
    class Meta:
        model = Turno
        fields = ["tratamiento", "fecha_asistencia", "estado", "nota"]
        widgets = {
            "fecha_asistencia": forms.DateTimeInput(attrs={"type": "datetime-local", "class": "form-control"}),
            "tratamiento": forms.Select(attrs={"class": "form-select"}),
            "estado": forms.Select(attrs={"class": "form-select"}),
            "nota": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }

    def __init__(self, *args, paciente=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.paciente = paciente
        tratamientos = Tratamiento.objects.filter(
            agenda_categoria=Tratamiento.AgendaCategoria.CONSULTORIO,
            duracion_tratamiento__in=[timedelta(minutes=30)],
        )
        if paciente:
            indicados = Evolucion.objects.filter(
                historia_clinica__paciente=paciente,
                tratamiento_indicado__isnull=False,
            ).values_list("tratamiento_indicado_id", flat=True)
            tratamientos = tratamientos | Tratamiento.objects.filter(pk__in=indicados)
        self.fields["tratamiento"].queryset = tratamientos.distinct().order_by(
            "agenda_categoria", "nombre_tratamiento"
        )
        self.fields["estado"].choices = [
            (Turno.Estado.RESERVADO, Turno.Estado.RESERVADO.label),
            (Turno.Estado.ASIGNADO, Turno.Estado.ASIGNADO.label),
        ]
        self.fields["nota"].required = False

    def clean(self):
        cleaned = super().clean()
        tratamiento = cleaned.get("tratamiento")
        fecha = cleaned.get("fecha_asistencia")
        estado = cleaned.get("estado")

        if not tratamiento or not fecha:
            return cleaned
        if timezone.is_naive(fecha):
            fecha = timezone.make_aware(fecha, timezone.get_current_timezone())
            cleaned["fecha_asistencia"] = fecha
        if fecha <= timezone.now():
            self.add_error("fecha_asistencia", "Elegí una fecha y hora futuras.")
            return cleaned

        inicio_dia = fecha.weekday()
        categoria = tratamiento.agenda_categoria
        hora = fecha.time()
        duracion = tratamiento.duracion_tratamiento

        if categoria == Tratamiento.AgendaCategoria.MTC:
            bloques_validos = {datetime.min.replace(hour=8).time(), datetime.min.replace(hour=14).time()}
            if inicio_dia > 4 or hora not in bloques_validos or duracion != timedelta(hours=6):
                self.add_error("fecha_asistencia", "MTC se agenda de lunes a viernes a las 8:00 o a las 14:00.")
        elif categoria in {Tratamiento.AgendaCategoria.NTF, Tratamiento.AgendaCategoria.PRP}:
            if inicio_dia == 5:
                hora_apertura, hora_cierre = timezone.datetime(2000, 1, 1, 9).time(), timezone.datetime(2000, 1, 1, 17).time()
            elif inicio_dia < 5:
                hora_apertura, hora_cierre = timezone.datetime(2000, 1, 1, 8).time(), timezone.datetime(2000, 1, 1, 20).time()
            else:
                self.add_error("fecha_asistencia", "La agenda de NTF y PRP está disponible de lunes a sábado.")
                return cleaned
            if hora < hora_apertura or fecha + duracion > timezone.make_aware(
                datetime.combine(fecha.date(), hora_cierre), timezone.get_current_timezone()
            ):
                self.add_error("fecha_asistencia", "El horario queda fuera de la jornada de esta prestación.")
        else:
            if inicio_dia > 4:
                self.add_error("fecha_asistencia", "Las prestaciones del consultorio se agendan de lunes a viernes.")
            hora_apertura = datetime.min.replace(hour=8).time()
            hora_cierre = datetime.min.replace(hour=20).time()
            cierre = timezone.make_aware(
                datetime.combine(fecha.date(), hora_cierre), timezone.get_current_timezone()
            )
            if hora < hora_apertura or fecha + duracion > cierre:
                self.add_error("fecha_asistencia", "El horario queda fuera de la jornada del consultorio.")

        intervalo = int(duracion.total_seconds() // 60)
        if categoria != Tratamiento.AgendaCategoria.MTC and (
            fecha.minute % intervalo != 0 or fecha.second or fecha.microsecond
        ):
            self.add_error("fecha_asistencia", f"Los turnos deben comenzar en intervalos de {intervalo} minutos.")

        if self.paciente and tratamiento.requiere_plan:
            indicaciones = Evolucion.objects.filter(
                historia_clinica__paciente=self.paciente,
                tratamiento_indicado=tratamiento,
            ).order_by("-fecha_evolucion", "-id")
            indicacion = indicaciones.first()
            if not indicacion:
                self.add_error("tratamiento", "Este tratamiento debe estar indicado por un médico antes de agendar.")
                return cleaned
            cleaned["indicacion_medica"] = indicacion
            plan = PlanPago.objects.filter(
                dni=self.paciente,
                tratamiento=tratamiento,
                estado="activo",
                sesiones_consumidas__lt=F("sesiones_total"),
            ).order_by("-fecha_inicio_tratamiento", "-id_plan").first()
            cleaned["plan"] = plan

        conflicto = False
        for otro in Turno.objects.filter(
            estado__in=[Turno.Estado.RESERVADO, Turno.Estado.ASIGNADO]
        ).exclude(pk=self.instance.pk):
            otro_inicio = otro.fecha_asistencia
            otra_duracion = (
                otro.tratamiento.duracion_tratamiento
                if otro.tratamiento_id
                else timedelta(minutes=30)
            )
            if (
                otro.tratamiento.agenda_categoria == categoria
                and fecha < otro_inicio + otra_duracion
                and otro_inicio < fecha + duracion
            ):
                conflicto = True
                break
        if conflicto:
            self.add_error("fecha_asistencia", "Ese horario se superpone con otro turno. Elegí otro horario.")

        return cleaned


class SeleccionarPacienteTurnoForm(forms.Form):
    paciente = forms.ModelChoiceField(
        queryset=Paciente.objects.order_by("apellido_paciente", "nombre_paciente"),
        empty_label="Seleccionar paciente...",
        widget=forms.Select(attrs={"class": "form-select"}),
    )


class TratamientoIndicadoForm(forms.Form):
    tratamiento_indicado = forms.ModelChoiceField(
        queryset=Tratamiento.objects.filter(requiere_plan=True).order_by("nombre_tratamiento"),
        required=False,
        label="Tratamiento indicado",
        empty_label="Sin tratamiento indicado",
        widget=forms.Select(attrs={"class": "form-select"}),
    )