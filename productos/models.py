from django.db import models

class Producto(models.Model):
    codigo_producto = models.SmallIntegerField(primary_key=True) 
    nombre_producto = models.CharField(max_length=20)
    cantidad_producto = models.SmallIntegerField(default=0)
    categoria_producto = models.CharField(max_length=20)
    precio_producto = models.IntegerField()
    stock_minimo = models.SmallIntegerField(default=5)
    
    def __str__(self):
        return self.nombre_producto 
    
    @property
    def stock_bajo(self):
        return self.cantidad_producto < self.stock_minimo
    
class Venta(models.Model):
    METODOS = [
        ("efectivo"), ("Efectivo"), ("debito"), ("Debito"),
        ("credito"), ("Credito"), ("transferencia"), ("Transferencia"),
    ]
        
    paciente = models.ForeignKey(
        "pacientes.Paciente", on_delete=models.PROTECT,
        null=True, blank=True,
        )
        
    metodo_pago = models.CharField(max_length=20)
    fecha_venta = models.DateTimeField(auto_now_add=True)
    total_venta = models.IntegerField()
        
    def __str__(self):
        return f"Venta #{self.id} - ${self.total_venta}"
        
        
        
class DetalleVenta (models.Model):
    venta = models.ForeignKey(Venta, on_delete=models.CASCADE, related_name="detalles")
    codigo_producto = models.ForeignKey(Producto, on_delete=models.PROTECT)
    cantidad_unitaria = models.IntegerField()
    precio_unitario = models.IntegerField()
    
    
#class Archivo(models.Model):
#    evaluacion = models.ForeignKey(
#    "pacientes.EvaluacionMedica", on_delete=models.CASCADE, related_name="archivos")
#    archivo_adjunto = models.FileField(upload_to="evaluaciones/") 