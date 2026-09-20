from django.contrib.auth.models import User
from django.test import TestCase

from pacientes.models import HistoriaClinica, Paciente, Evolucion
from usuarios.models import Profesional


class EvolucionModelTests(TestCase):
    def test_crea_evolucion_con_historia_clinica(self):
        usuario = User.objects.create_user(username="medico1", password="secret123")
        profesional = Profesional.objects.create(
            usuario=usuario,
            matricula="M-001",
            especialidad="Medicina general",
        )
        paciente = Paciente.objects.create(
            dni="12345678",
            nombre_paciente="Ana",
            apellido_paciente="García",
            fecha_nacimiento="1990-05-10",
            domicilio="Av. Siempre Viva 123",
            localidad="Rosario",
            correo_electronico="ana@example.com",
            telefono="3415551234",
            obra_social="OSDE",
            sexo="Mujer",
        )
        historia = HistoriaClinica.objects.create(paciente=paciente)

        evolucion = Evolucion.objects.create(
            historia_clinica=historia,
            profesional=profesional,
            tipo=Evolucion.Tipo.PRIVADA,
            resumen="Control de rutina",
            descripcion="Paciente sin novedades.",
            fecha_evolucion="2026-09-20",
        )

        self.assertEqual(evolucion.historia_clinica, historia)
        self.assertEqual(evolucion.profesional, profesional)
        self.assertEqual(evolucion.tipo, Evolucion.Tipo.PRIVADA)