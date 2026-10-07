from datetime import timedelta

from django.db import migrations


def configurar_agendas(apps, schema_editor):
    Tratamiento = apps.get_model("tratamientos", "Tratamiento")
    configuraciones = {
        "Primera consulta": ("consultorio", timedelta(minutes=30)),
        "Nueva evaluación": ("consultorio", timedelta(minutes=30)),
        "Control de Nutrifol": ("consultorio", timedelta(minutes=30)),
        "Control de PRP": ("consultorio", timedelta(minutes=30)),
        "Control de medicación": ("consultorio", timedelta(minutes=30)),
        "MTC": ("mtc", timedelta(hours=6)),
        "NTF": ("ntf", timedelta(minutes=15)),
        "PRP": ("prp", timedelta(minutes=30)),
    }

    for nombre, (categoria, duracion) in configuraciones.items():
        Tratamiento.objects.filter(nombre_tratamiento=nombre).update(
            agenda_categoria=categoria,
            duracion_tratamiento=duracion,
        )


def restaurar_agendas(apps, schema_editor):
    Tratamiento = apps.get_model("tratamientos", "Tratamiento")
    duraciones_originales = {
        "Primera consulta": timedelta(minutes=30),
        "Nueva evaluación": timedelta(minutes=30),
        "Control de Nutrifol": timedelta(minutes=15),
        "Control de PRP": timedelta(minutes=15),
        "Control de medicación": timedelta(minutes=15),
        "MTC": timedelta(minutes=60),
        "NTF": timedelta(minutes=15),
        "PRP": timedelta(minutes=30),
    }

    for nombre, duracion in duraciones_originales.items():
        Tratamiento.objects.filter(nombre_tratamiento=nombre).update(
            agenda_categoria="consultorio",
            duracion_tratamiento=duracion,
        )


class Migration(migrations.Migration):
    dependencies = [
        ("tratamientos", "0006_tratamiento_agenda_categoria"),
    ]

    operations = [
        migrations.RunPython(configurar_agendas, restaurar_agendas),
    ]