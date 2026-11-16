from django.db import migrations


PRECIOS_ACTUALIZADOS = {
    "Primera consulta": 30000,
    "Nueva evaluación": 30000,
    "Control de Nutrifol": 30000,
    "Control de PRP": 30000,
    "Control de medicación": 30000,
    "MTC": 3000000,
    "NTF": 600000,
    "PRP": 600000,
}

PRECIOS_ANTERIORES = {
    "Primera consulta": 50000,
    "Nueva evaluación": 50000,
    "Control de Nutrifol": 50000,
    "Control de PRP": 50000,
    "Control de medicación": 50000,
    "MTC": 4500000,
    "NTF": 822800,
    "PRP": 822800,
}


def actualizar_precios(apps, schema_editor):
    Tratamiento = apps.get_model("tratamientos", "Tratamiento")
    tratamientos = Tratamiento.objects.using(schema_editor.connection.alias)
    for nombre, precio in PRECIOS_ACTUALIZADOS.items():
        tratamientos.filter(nombre_tratamiento=nombre).update(precio_total=precio)


def restaurar_precios(apps, schema_editor):
    Tratamiento = apps.get_model("tratamientos", "Tratamiento")
    tratamientos = Tratamiento.objects.using(schema_editor.connection.alias)
    for nombre, precio in PRECIOS_ANTERIORES.items():
        tratamientos.filter(nombre_tratamiento=nombre).update(precio_total=precio)


class Migration(migrations.Migration):
    dependencies = [
        ("tratamientos", "0007_configurar_agendas"),
    ]

    operations = [
        migrations.RunPython(actualizar_precios, restaurar_precios),
    ]
