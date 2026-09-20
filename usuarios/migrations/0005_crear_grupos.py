from django.db import migrations


def crear_grupos(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    grupos = ["CEO", "Recepcionista", "Médico", "Enfermero", "Instrumentador", "Administrativo"]
    for nombre in grupos:
        Group.objects.get_or_create(name=nombre)


def borrar_grupos(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    grupos = ["CEO", "Recepcionista", "Médico", "Enfermero", "Instrumentador", "Administrativo"]
    Group.objects.filter(name__in=grupos).delete()

class Migration(migrations.Migration):

    dependencies = [
        ('usuarios', '0004_movimientocaja_categoria_movimiento_and_more'),
    ]

    operations = [
        migrations.RunPython(crear_grupos, borrar_grupos),
    ]
