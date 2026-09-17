from django.db import models
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
        return f"{self.nombreusuario} { self.apellidoUsuario} ({self.rolUsuario})"

# Create your models here.
