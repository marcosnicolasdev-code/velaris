from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("pacientes", "0011_turno_indicacion_medica_turno_nota"),
    ]

    operations = [
        migrations.CreateModel(
            name="NotaAgenda",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("fecha", models.DateField(unique=True)),
                ("texto", models.TextField()),
                ("actualizado_en", models.DateTimeField(auto_now=True)),
            ],
        ),
    ]