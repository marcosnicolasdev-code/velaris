from datetime import timedelta
from django.db import migrations


def cargar_tratamientos(apps, schema_editor):
    Tratamiento = apps.get_model("tratamientos", "Tratamiento")

    tratamientos = [
        # nombre, sesiones, duracion (minutos), precio_total, requiere_plan
        ("Primera consulta",        1, 30,   50000,   False),
        ("Nueva evaluación",        1, 30,   50000,   False),
        ("Control de Nutrifol",     1, 15,   50000,   False),
        ("Control de PRP",          1, 15,   50000,   False),
        ("Control de medicación",   1, 15,   50000,   False),
        ("MTC",                     1, 60,   4500000, True),
        ("NTF",                     12, 15,  822800,  True),
        ("PRP",                     3, 30,   822800,  True),
    ]

    for nombre, sesiones, minutos, precio, requiere in tratamientos:
        # El tratamiento se crea solo si no existe
        Tratamiento.objects.get_or_create(
            nombre_tratamiento=nombre,
            # Usa los valores precargados arriba
            defaults={
                "sesion_tratamiento": sesiones,
                "duracion_tratamiento": timedelta(minutes=minutos),
                "precio_total": precio,
                "requiere_plan": requiere,
            },
        )


def borrar_tratamientos(apps, schema_editor):
    Tratamiento = apps.get_model("tratamientos", "Tratamiento")
    nombres = [
        "Primera consulta", "Nueva evaluación", "Control de Nutrifol",
        "Control de PRP", "Control de medicación", "MTC", "NTF", "PRP",
    ]
    Tratamiento.objects.filter(nombre_tratamiento__in=nombres).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('tratamientos', '0003_tratamiento_precio_total_tratamiento_requiere_plan'),
    ]

    operations = [
        migrations.RunPython(cargar_tratamientos, borrar_tratamientos),
    ]
