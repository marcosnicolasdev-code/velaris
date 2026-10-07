from django.contrib.auth.models import Group, Permission, User
from django.contrib.contenttypes.models import ContentType
from django.db.models.signals import m2m_changed
from django.dispatch import receiver

from .models import Caja

GRUPOS_CON_ACCESO_ADMIN = {
    "CEO",
    "Recepcionista",
    "Médico",
    "Enfermero",
    "Instrumentador",
    "Administrativo",
}

PERMISOS_POR_GRUPO = {
    "CEO": ["paciente", "historiaclinica", "turno", "evolucion", "evaluacionmedica", "tratamiento", "planpago", "sesion", "receta", "profesional", "caja", "movimientocaja"],
    "Recepcionista": ["paciente", "historiaclinica", "turno", "evolucion", "planpago", "sesion", "caja", "movimientocaja"],
    "Médico": ["paciente", "historiaclinica", "turno", "evolucion", "evaluacionmedica", "tratamiento", "planpago", "sesion", "receta", "profesional"],
    "Enfermero": ["paciente", "historiaclinica", "turno", "evolucion"],
    "Instrumentador": ["paciente", "historiaclinica", "turno", "evolucion"],
    "Administrativo": ["paciente", "turno", "planpago", "sesion", "caja", "movimientocaja"],
}


def _dar_permisos_por_grupo(grupo_nombre):
    grupo = Group.objects.filter(name=grupo_nombre).first()
    if grupo is None:
        return

    permisos = Permission.objects.none()
    for modelo in PERMISOS_POR_GRUPO.get(grupo_nombre, []):
        content_type = ContentType.objects.filter(model=modelo).first()
        if content_type is not None:
            permisos = permisos | Permission.objects.filter(content_type=content_type)

    grupo.permissions.set(permisos)


@receiver(m2m_changed, sender=User.groups.through)
def crear_caja_por_rol(sender, instance, action, **kwargs):
    if action != "post_add":
        return

    grupos = set(instance.groups.values_list("name", flat=True))

    for nombre in GRUPOS_CON_ACCESO_ADMIN:
        if nombre in grupos:
            _dar_permisos_por_grupo(nombre)
            instance.is_staff = True
            instance.save(update_fields=["is_staff"])
            break

    if "Recepcionista" in grupos or "Administrativo" in grupos:
        if not Caja.objects.filter(usuario=instance).exists():
            Caja.objects.create(usuario=instance)