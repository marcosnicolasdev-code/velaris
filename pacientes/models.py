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
    sexo = models.CharField(max_length=1, blank=True)

    def __str__(self):
        return f"{self.apellido_paciente}, {self.nombre_paciente}"

class HistoriaClinica(models.Model):
    paciente = models.OneToOneField(Paciente, on_delete=models.PROTECT)

    def __str__(self):
        return f"HC de {self.paciente}"

class Turno(models.Model):
    class Estado(models.TextChoices):
        RESERVADO = "reservado", "Reservado"
        ASIGNADO = "asignado", "Asignado"
        FINALIZADO = "finalizado", "Finalizado"
        AUSENTE = "ausente", "Ausente"

    paciente = models.ForeignKey(Paciente, on_delete=models.PROTECT)
    tratamiento = models.ForeignKey(
        "tratamientos.Tratamiento",
        on_delete=models.PROTECT
    )
    estado = models.CharField(
        max_length=20,
        choices=Estado.choices,
        default=Estado.ASIGNADO
    )
    fecha_asistencia = models.DateTimeField()

    def __str__(self):
        return f"{self.paciente} - {self.fecha_asistencia}"    

class EvaluacionMedica(models.Model):
    historia_clinica = models.ForeignKey(
        HistoriaClinica,
        on_delete=models.PROTECT,
        related_name="evaluaciones"
    )
    profesional = models.ForeignKey(
        "usuarios.Profesional",
        on_delete=models.PROTECT
    )
    fecha_evaluacion = models.DateField()
    descripcion = models.TextField()




