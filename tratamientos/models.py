from django.db import models
class Tratamiento(models.Model):
 id_tratamiento = models.AutoField(primary_key=True) 
 nombre_tratamiento = models.CharField(max_length=100, null=True, blank=True)
 duracion_tratamiento = models.DurationField() 
 sesion_tratamiento = models.SmallIntegerField(default=1)
 precio_total = models.IntegerField(default=0)
 requiere_plan = models.BooleanField(default=False)

 def __str__(self): 
   return str(self.nombre_tratamiento)

 @property
 def precio_por_sesion(self):
      if self.sesion_tratamiento > 0:
        return round(self.precio_total / self.sesion_tratamiento) # Redondea la cuota por sesión  
      return self.precio_total
class PlanPago(models.Model):
  METODO_PAGO_CHOICES= [
    ('efectivo', 'Efectivo'),
    ('transferencia', 'Transferencia'),
    ('mercadopago', 'MercadoPago'),
    ('tarjeta_debito', 'Tarjeta Debito'),
    ('tarjeta_credito','Tarjeta Credito')
  ]
  ESTADOS = [("activo", "Activo"), ("completado", "Completado")]

  id_plan = models.AutoField(primary_key=True)
  dni = models.ForeignKey("pacientes.Paciente", on_delete=models.PROTECT)
  #id_venta = models.ForeignKey("ventas.Venta", on_delete=models.PROTECT)
  tratamiento = models.ForeignKey("Tratamiento", on_delete=models.PROTECT)
  valor_sesion = models.IntegerField()
  fecha_inicio_tratamiento = models.DateField(auto_now_add=True)
  metodo_pago= models.CharField(max_length=20, choices= METODO_PAGO_CHOICES, default='efectivo')

  sesiones_total = models.SmallIntegerField()
  sesiones_consumidas = models.SmallIntegerField(default=0)
  estado = models.CharField(max_length=20, choices=ESTADOS, default="activo")

  @property
  def sesiones_restantes(self):
    return self.sesiones_total - self.sesiones_consumidas

  def __str__(self): 
    return f"{self.dni} - {self.tratamiento} ({self.sesiones_restantes})" 

class Sesion(models.Model): 
  ESTADOS_PAGO = [("pendiente", "Pendiente"), ("abonado", "Abonado")]
  id_sesion = models.IntegerField(primary_key=True)
  #id_plan = models.ForeignKey("Tratamiento.PlanPago", on_delete=models.CASCADE)
  #id_turno = models.ForeignKey("pacientes.Turno", on_delete=models.PROTECT)
  duracion_sesion = models.DurationField() 
  numero_sesion = models.SmallIntegerField()
  estado_pago = models.CharField(max_length=20, choices=ESTADOS_PAGO, default="pendiente")

class Receta(models.Model):
  numero_receta = models.IntegerField(primary_key=True)
  #dni = models.ForeignKey("pacientes.Paciente", on_delete=models.PROTECT)
  #id_profesional = models.ForeignKey("usuarios.Profesional", on_delete=models.PROTECT)
  #codigo_producto = models.ForeignKey("productos.Producto", on_delete=models.PROTECT) 
  #id_historia_clinica = models.ForeignKey("pacientes.HistoriaClinica", on_delete=models.PROTECT)
  fecha_receta = models.DateField(auto_now_add=True)
  dosis = models.SmallIntegerField() 
  frecuencia = models.CharField(max_length=20, blank=True) 
  duracion_indicacion = models.CharField(max_length=20)
