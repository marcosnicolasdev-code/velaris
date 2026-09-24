from datetime import date
from django.conf import settings
from django.db import models


class Paciente(models.Model):
    dni = models.CharField(max_length=20, primary_key=True)
    nombre_paciente = models.CharField(max_length=20)
    apellido_paciente = models.CharField(max_length=20)
    fecha_nacimiento = models.DateField()
    domicilio = models.CharField(max_length=50, blank=True)
    localidad = models.CharField(max_length=50, blank=True)
    correo_electronico = models.EmailField(max_length=50)
    telefono = models.CharField(max_length=20)
    obra_social = models.CharField(max_length=20, blank=True)
    sexo = models.CharField(max_length=10, blank=True)

    @property
    def edad(self):
        hoy = date.today()
        edad = hoy.year - self.fecha_nacimiento.year

        if (hoy.month, hoy.day) < (
            self.fecha_nacimiento.month,
            self.fecha_nacimiento.day,
        ):
            edad -= 1

        return edad

    def __str__(self):
        return f"{self.apellido_paciente}, {self.nombre_paciente}"

    def get_historia_clinica(self):
        return HistoriaClinica.objects.get_or_create(paciente=self)[0]


class HistoriaClinica(models.Model):
    paciente = models.OneToOneField(Paciente, on_delete=models.PROTECT, related_name="historia_clinica")

    def __str__(self):
        return f"HC de {self.paciente}"


class Turno(models.Model):
    class Estado(models.TextChoices):
        RESERVADO = "reservado", "Reservado"
        ASIGNADO = "asignado", "Asignado"
        FINALIZADO = "finalizado", "Finalizado"
        AUSENTE = "ausente", "Ausente"
        CANCELADO = "cancelado", "Cancelado"

    plan = models.ForeignKey(
        "tratamientos.PlanPago",
        on_delete=models.PROTECT,
        null=True, blank=True,
    )
    paciente = models.ForeignKey(Paciente, on_delete=models.PROTECT)
    tratamiento = models.ForeignKey(
        "tratamientos.Tratamiento",
        on_delete=models.PROTECT,
    )
    estado = models.CharField(
        max_length=20,
        choices=Estado.choices,
        default=Estado.ASIGNADO,
    )
    fecha_asistencia = models.DateTimeField()

    def __str__(self):
        return f"{self.paciente} - {self.fecha_asistencia}"


class Evolucion(models.Model):
    class Tipo(models.TextChoices):
        CONTROL_MTC = "control_mtc", "Control MTC"
        CONTROL_NTF = "control_ntf", "Control NTF"
        CONTROL_PRP = "control_prp", "Control PRP"
        MTC = "mtc", "MTC"
        NTF = "ntf", "NTF"
        NUEVA_EVALUACION = "nueva_evaluacion", "Nueva evaluación"
        PRIMERA_CONSULTA = "primera_consulta", "Primera consulta"
        PRIVADA = "privada", "Privada"
        PRP = "prp", "PRP"

    historia_clinica = models.ForeignKey(
        HistoriaClinica,
        on_delete=models.PROTECT,
        related_name="evoluciones",
    )
    turno = models.ForeignKey(
        Turno,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="evoluciones",
    )
    profesional = models.ForeignKey(
        "usuarios.Profesional",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="evoluciones",
    )
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="evoluciones_creadas",
    )
    tipo = models.CharField(
        max_length=20,
        choices=Tipo.choices,
        default=Tipo.PRIVADA,
    )
    fecha_evolucion = models.DateField()
    numero_sesion = models.PositiveIntegerField(null=True, blank=True)
    resumen = models.CharField(max_length=200, blank=True)
    descripcion = models.TextField(blank=True)
    archivo = models.FileField(upload_to="evoluciones/%Y/%m/%d/", blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.get_tipo_display()} - {self.fecha_evolucion}"


class EvaluacionMedica(models.Model):
    historia_clinica = models.ForeignKey(
        HistoriaClinica,
        on_delete=models.PROTECT,
        related_name="evaluaciones",
    )
    profesional = models.ForeignKey(
        "usuarios.Profesional",
        on_delete=models.PROTECT,
    )
    fecha_evaluacion = models.DateField()
    descripcion = models.TextField()


