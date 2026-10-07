from django.db import migrations


def crear_permisos_grupos(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")
    ContentType = apps.get_model("contenttypes", "ContentType")

    permisos_por_grupo = {
        "CEO": ["paciente", "historiaclinica", "turno", "evolucion", "evaluacionmedica", "tratamiento", "planpago", "sesion", "receta", "profesional", "caja", "movimientocaja"],
        "Recepcionista": ["paciente", "historiaclinica", "turno", "evolucion", "planpago", "sesion", "caja", "movimientocaja"],
        "Médico": ["paciente", "historiaclinica", "turno", "evolucion", "evaluacionmedica", "tratamiento", "planpago", "sesion", "receta", "profesional"],
        "Enfermero": ["paciente", "historiaclinica", "turno", "evolucion"],
        "Instrumentador": ["paciente", "historiaclinica", "turno", "evolucion"],
        "Administrativo": ["paciente", "turno", "planpago", "sesion", "caja", "movimientocaja"],
    }

    for nombre_grupo, modelos in permisos_por_grupo.items():
        grupo = Group.objects.filter(name=nombre_grupo).first()
        if grupo is None:
            continue

        permisos = Permission.objects.none()
        for modelo in modelos:
            content_type = ContentType.objects.filter(model=modelo).first()
            if content_type is not None:
                permisos = permisos | Permission.objects.filter(content_type=content_type)

        grupo.permissions.set(permisos)


def borrar_permisos_grupos(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    for nombre in ["CEO", "Recepcionista", "Médico", "Enfermero", "Instrumentador", "Administrativo"]:
        grupo = Group.objects.filter(name=nombre).first()
        if grupo is not None:
            grupo.permissions.clear()


class Migration(migrations.Migration):

    dependencies = [
        ("usuarios", "0005_crear_grupos"),
    ]

    operations = [
        migrations.RunPython(crear_permisos_grupos, borrar_permisos_grupos),
    ]
