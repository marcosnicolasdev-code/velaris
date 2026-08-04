from django.db import models
from django.contrib.auth.models import User

class Profesional (models.Model):
    usuario = models.OneToOneField(User, on_delete=models.CASCADE)
    matricula = models.CharField(max_length=20)
    especialidad = models.CharField(max_length=20)

    def __str__(self):
        return f"{self.usuario.get_full_name()} - {self.especialidad}"

class Caja (models.Model):
    usuario = models.ForeignKey(User, on_delete=models.PROTECT)
    total_caja = models.IntegerField(default=0)
    apertura_caja = models.DateField(auto_now_add=True)
    cierre_caja = models.DateField(null=True, blank=True)

    def __str__(self):
        return f"Caja #{self.id}"

class MovimientoCaja (models.Model):
    TIPOS = [("ingreso", "Ingreso"), ("egreso", "Egreso")]

    caja = models.ForeignKey(Caja, on_delete=models.PROTECT, related_name="movimientos")
    tipo_movimiento = models.CharField(max_length=20, choices=TIPOS)
    importe_movimiento = models.IntegerField()
    fecha_movimiento = models.DateField(auto_now_add=True)

    def __str__(self):
        return f"{self.tipo_movimiento.upper()} - ${self.importe_movimiento} (Caja #{self.caja.id})"
    