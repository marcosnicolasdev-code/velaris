from django.db import models
from django.contrib.auth.models import User
from django.db.models import Sum

class Usuario(models.Model):
    ROLES = [
        ('admin', 'Admin'),
        ('empleado', 'Empleado'),
        ('cliente', 'Cliente'),
    ]
    id_usuario=models.AutoField(primary_key=True)
    nombre_Usuario = models.CharField(max_length = 100)
    apellido_Usuario = models.CharField(max_length = 100)
    contrasena = models.CharField(max_length=128)
    rol_Usuario = models.CharField(max_length=20, choices = ROLES, default='empleado')

    def __str__(self):
        return f"{self.nombre_Usuario} { self.apellido_Usuario} ({self.rol_Usuario})"

class Profesional (models.Model):
    usuario = models.OneToOneField(User, on_delete=models.CASCADE)
    matricula = models.CharField(max_length=20)
    especialidad = models.CharField(max_length=20)

    def __str__(self):
        return f"{self.usuario.get_full_name()} - {self.especialidad}"

class Caja (models.Model):
    usuario = models.OneToOneField(User, on_delete=models.PROTECT)
    total_caja = models.IntegerField(default=0)
    apertura_caja = models.DateTimeField(auto_now_add=True)
    cierre_caja = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Caja #{self.id}"

    @property
    def saldo(self):
        ingresos = self.movimientos.filter(tipo_movimiento="ingreso").aggregate(
            total=Sum("importe_movimiento"))["total"] or 0
        egresos = self.movimientos.filter(tipo_movimiento="egreso").aggregate(
            total=Sum("importe_movimiento"))["total"] or 0
        return ingresos - egresos

class MovimientoCaja (models.Model):
    TIPOS = [("ingreso", "Ingreso"), ("egreso", "Egreso")]
    CATEGORIAS = [("venta", "Venta"), ("pago_proveedor", "Pago a Proveedor"), ("pago_servicio", "Pago de Servicio"), ("pago_impuesto", "Pago de impuesto"), ("otro", "Otro")]

    caja = models.ForeignKey(Caja, on_delete=models.PROTECT, related_name="movimientos")
    tipo_movimiento = models.CharField(max_length=20, choices=TIPOS)
    categoria_movimiento = models.CharField(max_length=20, choices=CATEGORIAS, default="otro")
    descripcion_movimiento = models.CharField(max_length=200, blank=True)
    importe_movimiento = models.IntegerField()
    fecha_movimiento = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.tipo_movimiento.upper()} - ${self.importe_movimiento} (Caja #{self.caja.id})"
    