from django.db import models


class Paciente(models.Model):
    dni = models.CharField(max_length=20, primary_key=True)
    nombrePaciente = models.CharField(max_length=20)
    apellidoPaciente = models.CharField(max_length=20)
    fechaNacimiento = models.DateField()
    domicilio = models.CharField(max_length=50, blank=True)
    localidad = models.CharField(max_length=50, blank=True)
    correoElectronico = models.EmailField(max_length=50)
    telefono = models.CharField(max_length=20)
    obraSocial = models.CharField(max_length=20, blank=True)
    sexo = models.CharField(max_length=1, blank=True)

    def __str__(self):
        return f"{self.apellidoPaciente}, {self.nombrePaciente}"