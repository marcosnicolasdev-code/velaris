from datetime import timedelta

from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from pacientes.models import Evolucion, HistoriaClinica, Paciente, Turno
from tratamientos.models import PlanPago, Tratamiento


class PlanPaymentAssociationTests(TestCase):
	def test_pago_activa_el_plan_y_asocia_turnos_futuros_indicados(self):
		paciente = Paciente.objects.create(
			dni="99887766",
			nombre_paciente="Maria",
			apellido_paciente="Fernandez",
			fecha_nacimiento="1988-04-15",
			domicilio="Calle 1",
			localidad="Rosario",
			correo_electronico="maria@example.com",
			telefono="3415551111",
			obra_social="OSDE",
			sexo="Femenino",
		)
		tratamiento = Tratamiento.objects.get(nombre_tratamiento="NTF")
		historia = HistoriaClinica.objects.create(paciente=paciente)
		indicacion = Evolucion.objects.create(
			historia_clinica=historia,
			tratamiento_indicado=tratamiento,
			fecha_evolucion=timezone.localdate(),
			descripcion="Indicacion NTF",
		)
		fecha_turno = timezone.now() + timedelta(days=8)
		while fecha_turno.weekday() > 4:
			fecha_turno += timedelta(days=1)
		turno = Turno.objects.create(
			paciente=paciente,
			tratamiento=tratamiento,
			indicacion_medica=indicacion,
			fecha_asistencia=fecha_turno.replace(hour=10, minute=0, second=0, microsecond=0),
			estado=Turno.Estado.ASIGNADO,
		)
		usuario = User.objects.create_user(username="caja_recepcion", password="secret123")
		grupo, _ = Group.objects.get_or_create(name="Recepcionista")
		usuario.groups.add(grupo)
		self.client.force_login(usuario)

		respuesta = self.client.post(
			reverse("planpago_cobrar", kwargs={"dni": paciente.dni}),
			{"tratamiento": tratamiento.pk, "metodo_pago": "efectivo"},
		)

		self.assertRedirects(
			respuesta,
			reverse("paciente_detalle", kwargs={"dni": paciente.dni}),
		)
		plan = PlanPago.objects.get(dni=paciente, tratamiento=tratamiento)
		turno.refresh_from_db()
		self.assertEqual(turno.plan, plan)
		self.assertEqual(plan.sesiones_total, tratamiento.sesion_tratamiento)
