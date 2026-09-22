from django.db import models
<<<<<<< HEAD
class Tratamiento(models.Model): 
 id_tratamiento = models.CharField(max_length=20, primary_key=True)
 duracion_tratamiento = models.DurationField() 
 sesion_tratamiento = models.SmallIntegerField(default=1)
 def __str__(self): return self.id_tratamiento

class PlanPago(models.Model): 
  id_plan = models.AutoField(primary_key=True)
  dni = models.ForeignKey("pacientes.Paciente", on_delete=models.PROTECT)
  valor_sesion = models.IntegerField()
  fecha_inicio_tratamiento = models.DateField()
  def __str__(self): return f"Plan {self.id_plan} - {self.dni}" 
=======
class Tratamiento(models.Model):
 id_tratamiento = models.AutoField(primary_key=True) 
 nombre_tratamiento = models.CharField(max_length=100, null=True, blank=True)
 duracion_tratamiento = models.DurationField() 
 sesion_tratamiento = models.SmallIntegerField(default=1)
 def __str__(self): return str(self.nombre_tratamiento)

class PlanPago(models.Model):
  METODO_PAGO_CHOICES= [
    ('efectivo', 'Efectivo'),
    ('transferencia', 'Transferencia'),
    ('mercadopago', 'MercadoPago'),
    ('tarjeta_debito', 'Tarjeta Debito'),
    ('tarjeta_credito','Tarjeta Credito')
  ]
  id_plan = models.AutoField(primary_key=True)
  #dni = models.ForeignKey("pacientes.Paciente", on_delete=models.PROTECT)
  #id_venta = models.ForeignKey("ventas.Venta", on_delete=models.PROTECT)
  nombre_tratamiento = models.ForeignKey("Tratamiento", on_delete=models.CASCADE, null=True, blank=True)
  valor_sesion = models.IntegerField()
  fecha_inicio_tratamiento = models.DateField()
  metodo_pago= models.CharField(max_length=20, choices= METODO_PAGO_CHOICES, default='efectivo', verbose_name="Metodo de pago")
  def __str__(self): return f"{self.nombre_tratamiento} - {self.metodo_pago}-${self.valor_sesion}" 
>>>>>>> feature/models-tratamientos

class Sesion(models.Model): 
  ESTADOS_PAGO = [("pendiente", "Pendiente"), ("abonado", "Abonado")]
  id_sesion = models.IntegerField(primary_key=True)
<<<<<<< HEAD
  id_plan = models.ForeignKey(PlanPago, on_delete=models.PROTECT, related_name="sesiones")
  id_turno = models.ForeignKey("pacientes.Turno", on_delete=models.PROTECT)
=======
  #id_plan = models.ForeignKey("Tratamiento.PlanPago", on_delete=models.CASCADE)
  #id_turno = models.ForeignKey("pacientes.Turno", on_delete=models.PROTECT)
>>>>>>> feature/models-tratamientos
  duracion_sesion = models.DurationField() 
  numero_sesion = models.SmallIntegerField()
  estado_pago = models.CharField(max_length=20, choices=ESTADOS_PAGO, default="pendiente")

class Receta(models.Model):
  numero_receta = models.IntegerField(primary_key=True)
<<<<<<< HEAD
  dni = models.ForeignKey("pacientes.Paciente", on_delete=models.PROTECT)
  id_profesional = models.ForeignKey("usuarios.Profesional", on_delete=models.PROTECT)
  codigo_producto = models.ForeignKey("productos.Producto", on_delete=models.PROTECT) 
  id_historia_clinica = models.ForeignKey("pacientes.HistoriaClinica", on_delete=models.PROTECT)
=======
  #dni = models.ForeignKey("pacientes.Paciente", on_delete=models.PROTECT)
  #id_profesional = models.ForeignKey("usuarios.Profesional", on_delete=models.PROTECT)
  #codigo_producto = models.ForeignKey("productos.Producto", on_delete=models.PROTECT) 
  #id_historia_clinica = models.ForeignKey("pacientes.HistoriaClinica", on_delete=models.PROTECT)
>>>>>>> feature/models-tratamientos
  fecha_receta = models.DateField(auto_now_add=True)
  dosis = models.SmallIntegerField() 
  frecuencia = models.CharField(max_length=20, blank=True) 
  duracion_indicacion = models.CharField(max_length=20)
<<<<<<< HEAD
# Create your models here.
=======
>>>>>>> feature/models-tratamientos
