from django.db import models
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
class Sesion(models.Model): 
  ESTADOS_PAGO = [("pendiente", "Pendiente"), ("abonado", "Abonado")]
  id_sesion = models.IntegerField(primary_key=True)
  id_plan = models.ForeignKey(PlanPago, on_delete=models.PROTECT, related_name="sesiones")
  id_turno = models.ForeignKey("pacientes.Turno", on_delete=models.PROTECT)
  duracion_sesion = models.DurationField() 
  numero_sesion = models.SmallIntegerField()
  estado_pago = models.CharField(max_length=20, choices=ESTADOS_PAGO, default="pendiente")
class Receta(models.Model):
  numero_receta = models.IntegerField(primary_key=True)
  dni = models.ForeignKey("pacientes.Paciente", on_delete=models.PROTECT)
  id_profesional = models.ForeignKey("usuarios.Profesional", on_delete=models.PROTECT)
  codigo_producto = models.ForeignKey("productos.Producto", on_delete=models.PROTECT) 
  id_historia_clinica = models.ForeignKey("pacientes.HistoriaClinica", on_delete=models.PROTECT)
  fecha_receta = models.DateField(auto_now_add=True)
  dosis = models.SmallIntegerField() 
  frecuencia = models.CharField(max_length=20, blank=True) 
  duracion_indicacion = models.CharField(max_length=20)
# Create your models here.
