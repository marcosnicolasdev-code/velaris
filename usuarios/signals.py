from django.db.models.signals import m2m_changed
from django.contrib.auth.models import User
from django.dispatch import receiver
from .models import Caja

# La funcion se ejecuta cuando cambia el grupo de un usuario.
@receiver(m2m_changed, sender=User.groups.through)
def crear_caja_por_rol(sender, instance, action, **kwargs):
    # Solo actua cuando se asigna un grupo al usuario (post_add)
    if action == "post_add":
        # El usuario pertenece a recepción o administración?
        grupos = instance.groups.values_list('name', flat=True) # Trae el nombre del grupo del usuario
        if "Recepcionista" in grupos or "Administrativo" in grupos:
            # El usuario ya tiene una caja? si no es asi, se la creamos
            if not Caja.objects.filter(usuario=instance).exists():
                Caja.objects.create(usuario=instance)