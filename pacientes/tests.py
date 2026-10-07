from datetime import timedelta

from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from pacientes.forms import AgendarTurnoForm
from pacientes.models import HistoriaClinica, Paciente, Evolucion, Turno
from tratamientos.models import PlanPago, Tratamiento
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


class AgendaTurnoEntryTests(TestCase):
    def test_nuevo_turno_permite_buscar_paciente_por_apellido(self):
        usuario = User.objects.create_user(username="recepcion", password="secret123")
        grupo_recepcion, _ = Group.objects.get_or_create(name="Recepcionista")
        usuario.groups.add(grupo_recepcion)
        self.client.force_login(usuario)
        paciente = Paciente.objects.create(
            dni="87654321",
            nombre_paciente="Ana",
            apellido_paciente="Pérez",
            fecha_nacimiento="1990-05-10",
            domicilio="Calle 123",
            localidad="Rosario",
            correo_electronico="ana@example.com",
            telefono="3415551234",
            obra_social="OSDE",
            sexo="Femenino",
        )

        agenda = self.client.get(reverse("agenda"))
        self.assertContains(agenda, "Nuevo turno")
        respuesta = self.client.get(
            reverse("nuevo_turno_agenda"),
            {"q": "Perez"},
        )

        self.assertContains(respuesta, paciente.dni)
        self.assertContains(respuesta, reverse("agendar_turno", kwargs={"dni": paciente.dni}))

    def test_agendar_turno_no_pide_plan_y_guarda_nota_y_estado(self):
        usuario = User.objects.create_user(username="recepcion_turnos", password="secret123")
        grupo, _ = Group.objects.get_or_create(name="Recepcionista")
        usuario.groups.add(grupo)
        self.client.force_login(usuario)
        paciente = Paciente.objects.create(
            dni="66778899",
            nombre_paciente="Elena",
            apellido_paciente="Díaz",
            fecha_nacimiento="1991-03-10",
            domicilio="Calle 10",
            localidad="Rosario",
            correo_electronico="elena@example.com",
            telefono="3415558888",
            obra_social="OSDE",
            sexo="Femenino",
        )
        tratamiento = Tratamiento.objects.get(nombre_tratamiento="Primera consulta")
        fecha = timezone.localdate() + timedelta(days=7)
        while fecha.weekday() > 4:
            fecha += timedelta(days=1)

        respuesta = self.client.post(
            reverse("agendar_turno", kwargs={"dni": paciente.dni}),
            {
                "tratamiento": tratamiento.pk,
                "fecha_asistencia": f"{fecha.isoformat()}T10:00",
                "estado": Turno.Estado.RESERVADO,
                "nota": "Confirmar por telefono",
            },
        )

        self.assertRedirects(respuesta, reverse("agenda"))
        turno = Turno.objects.get(paciente=paciente)
        self.assertIsNone(turno.plan)
        self.assertEqual(turno.estado, Turno.Estado.RESERVADO)
        self.assertEqual(turno.nota, "Confirmar por telefono")

    def test_reagendar_mantiene_paciente_prestacion_y_estado(self):
        usuario = User.objects.create_user(username="recepcion_reagenda", password="secret123")
        grupo, _ = Group.objects.get_or_create(name="Recepcionista")
        usuario.groups.add(grupo)
        self.client.force_login(usuario)
        paciente = Paciente.objects.create(
            dni="77889900",
            nombre_paciente="Pablo",
            apellido_paciente="Ruiz",
            fecha_nacimiento="1989-02-01",
            domicilio="Calle 20",
            localidad="Rosario",
            correo_electronico="pablo@example.com",
            telefono="3415557777",
            obra_social="OSDE",
            sexo="Masculino",
        )
        tratamiento = Tratamiento.objects.get(nombre_tratamiento="Primera consulta")
        fecha = timezone.localdate() + timedelta(days=7)
        while fecha.weekday() > 4:
            fecha += timedelta(days=1)
        turno = Turno.objects.create(
            paciente=paciente,
            tratamiento=tratamiento,
            fecha_asistencia=timezone.make_aware(
                timezone.datetime.combine(fecha, timezone.datetime.min.time().replace(hour=10))
            ),
            estado=Turno.Estado.RESERVADO,
            nota="Nota inicial",
        )

        respuesta = self.client.post(
            reverse("turno_editar", kwargs={"dni": paciente.dni, "turno_id": turno.pk}),
            {
                "tratamiento": tratamiento.pk,
                "fecha_asistencia": f"{fecha.isoformat()}T10:30",
                "estado": Turno.Estado.RESERVADO,
                "nota": "Nuevo horario confirmado",
            },
        )

        self.assertRedirects(respuesta, reverse("agenda"))
        turno.refresh_from_db()
        self.assertEqual(turno.paciente, paciente)
        self.assertEqual(turno.tratamiento, tratamiento)
        self.assertEqual(turno.estado, Turno.Estado.RESERVADO)
        self.assertEqual(turno.fecha_asistencia.minute, 30)
        self.assertEqual(turno.nota, "Nuevo horario confirmado")


class MedicalTreatmentIndicationTests(TestCase):
    def test_medico_guarda_el_tratamiento_indicado_en_la_evolucion(self):
        usuario = User.objects.create_user(username="medico2", password="secret123")
        grupo_medico, _ = Group.objects.get_or_create(name="Médico")
        usuario.groups.add(grupo_medico)
        Profesional.objects.create(
            usuario=usuario,
            matricula="M-002",
            especialidad="Medicina general",
        )
        paciente = Paciente.objects.create(
            dni="11223344",
            nombre_paciente="Lucía",
            apellido_paciente="Gómez",
            fecha_nacimiento="1990-05-10",
            domicilio="Calle 123",
            localidad="Rosario",
            correo_electronico="lucia@example.com",
            telefono="3415551234",
            obra_social="OSDE",
            sexo="Femenino",
        )
        tratamiento = Tratamiento.objects.create(
            nombre_tratamiento="NTF",
            duracion_tratamiento=timedelta(minutes=15),
            sesion_tratamiento=12,
            precio_total=0,
            requiere_plan=True,
        )
        self.client.force_login(usuario)

        respuesta = self.client.post(
            reverse("evolucion_profesional_crear", kwargs={"dni": paciente.dni}),
            {
                "tipo": "primera_consulta",
                "motivo": "Consulta inicial",
                "antecedentes": "",
                "examen_fisico": "",
                "se_indica": "Iniciar tratamiento",
                "tratamiento_indicado": tratamiento.pk,
            },
        )

        self.assertRedirects(
            respuesta,
            reverse("paciente_detalle", kwargs={"dni": paciente.dni}),
        )
        evolucion = Evolucion.objects.get(historia_clinica__paciente=paciente)
        self.assertEqual(evolucion.tratamiento_indicado, tratamiento)


class AgendaAvailabilityTests(TestCase):
    def setUp(self):
        self.paciente = Paciente.objects.create(
            dni="55667788",
            nombre_paciente="Sofía",
            apellido_paciente="López",
            fecha_nacimiento="1990-05-10",
            domicilio="Calle 123",
            localidad="Rosario",
            correo_electronico="sofia@example.com",
            telefono="3415551234",
            obra_social="OSDE",
            sexo="Femenino",
        )
        self.consulta = Tratamiento.objects.get(nombre_tratamiento="Primera consulta")
        self.ntf = Tratamiento.objects.get(nombre_tratamiento="NTF")
        self.mtc = Tratamiento.objects.get(nombre_tratamiento="MTC")
        historia = HistoriaClinica.objects.create(paciente=self.paciente)
        self.indicacion = Evolucion.objects.create(
            historia_clinica=historia,
            tratamiento_indicado=self.ntf,
            fecha_evolucion=timezone.localdate(),
            descripcion="Indica NTF",
        )

    def fecha_semana(self, hora, minuto=0, dias_adelante=7):
        dia = timezone.localdate() + timedelta(days=dias_adelante)
        while dia.weekday() > 4:
            dia += timedelta(days=1)
        return f"{dia.isoformat()}T{hora:02d}:{minuto:02d}"

    def test_consultorio_rechaza_inicios_que_no_respetan_bloques_de_media_hora(self):
        form = AgendarTurnoForm(
            {
                "tratamiento": self.consulta.pk,
                "fecha_asistencia": self.fecha_semana(10, 15),
                "estado": Turno.Estado.ASIGNADO,
                "nota": "",
            },
            paciente=self.paciente,
        )

        self.assertFalse(form.is_valid())
        self.assertIn("fecha_asistencia", form.errors)

    def test_ntf_solo_se_ofrece_si_esta_indicado_y_usa_bloques_de_quince_minutos(self):
        form = AgendarTurnoForm(
            {
                "tratamiento": self.ntf.pk,
                "fecha_asistencia": self.fecha_semana(10, 15),
                "estado": Turno.Estado.RESERVADO,
                "nota": "",
            },
            paciente=self.paciente,
        )

        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["indicacion_medica"], self.indicacion)
        self.assertIsNone(form.cleaned_data["plan"])

    def test_mtc_solo_admite_sus_dos_horarios_fijos(self):
        self.indicacion.tratamiento_indicado = self.mtc
        self.indicacion.save(update_fields=["tratamiento_indicado"])
        form = AgendarTurnoForm(
            {
                "tratamiento": self.mtc.pk,
                "fecha_asistencia": self.fecha_semana(12),
                "estado": Turno.Estado.ASIGNADO,
                "nota": "",
            },
            paciente=self.paciente,
        )

        self.assertFalse(form.is_valid())
        self.assertIn("fecha_asistencia", form.errors)

    def test_calendario_devuelve_solo_los_bloques_disponibles_de_la_agenda(self):
        usuario = User.objects.create_user(username="recepcion_agenda", password="secret123")
        grupo, _ = Group.objects.get_or_create(name="Recepcionista")
        usuario.groups.add(grupo)
        self.client.force_login(usuario)
        fecha = timezone.localdate() + timedelta(days=7)
        while fecha.weekday() > 4:
            fecha += timedelta(days=1)
        inicio = timezone.make_aware(timezone.datetime.combine(fecha, timezone.datetime.min.time().replace(hour=8)))
        Turno.objects.create(
            paciente=self.paciente,
            tratamiento=self.ntf,
            indicacion_medica=self.indicacion,
            fecha_asistencia=inicio,
            estado=Turno.Estado.ASIGNADO,
        )

        respuesta = self.client.get(
            reverse("agenda_disponibilidad_json"),
            {
                "tratamiento": self.ntf.pk,
                "dni": self.paciente.dni,
                "start": fecha.isoformat(),
                "end": (fecha + timedelta(days=1)).isoformat(),
            },
        )

        eventos = respuesta.json()
        ocupados = [
            evento for evento in eventos
            if not evento["extendedProps"].get("disponible")
            and not evento["extendedProps"].get("disponibilidadResumen")
        ]
        disponibles = [evento for evento in eventos if evento["extendedProps"]["disponible"]]
        resumen = next(evento for evento in eventos if evento["extendedProps"].get("disponibilidadResumen"))
        self.assertEqual(len(ocupados), 1)
        self.assertEqual(len(disponibles), 47)
        self.assertEqual(resumen["extendedProps"]["cantidadDisponible"], 47)
        self.assertIn("Sofía", ocupados[0]["title"])
        self.assertIn("Asignado", ocupados[0]["title"])

    def test_calendario_sin_tratamiento_muestra_disponibilidad_por_tratamiento_y_categoria(self):
        usuario = User.objects.create_user(username="recepcion_resumen", password="secret123")
        grupo, _ = Group.objects.get_or_create(name="Recepcionista")
        usuario.groups.add(grupo)
        self.client.force_login(usuario)
        fecha = timezone.localdate() + timedelta(days=7)
        while fecha.weekday() > 4:
            fecha += timedelta(days=1)

        respuesta = self.client.get(
            reverse("agenda_disponibilidad_json"),
            {
                "start": fecha.isoformat(),
                "end": (fecha + timedelta(days=7)).isoformat(),
            },
        )

        self.assertEqual(respuesta.status_code, 200)
        eventos = respuesta.json()
        resumenes = [evento for evento in eventos if evento["extendedProps"].get("resumenTratamiento")]
        resumenes_categoria = [evento for evento in eventos if evento["extendedProps"].get("resumenCategoria")]
        self.assertTrue(resumenes)
        self.assertTrue(resumenes_categoria)
        tratamientos_resumidos = {evento["extendedProps"]["tratamientoId"] for evento in resumenes}
        tratamientos_agendables = set(
            Tratamiento.objects.filter(
                agenda_categoria__in=[
                    Tratamiento.AgendaCategoria.CONSULTORIO,
                    Tratamiento.AgendaCategoria.MTC,
                    Tratamiento.AgendaCategoria.NTF,
                    Tratamiento.AgendaCategoria.PRP,
                ]
            ).values_list("pk", flat=True)
        )
        self.assertSetEqual(tratamientos_resumidos, tratamientos_agendables)
        self.assertEqual(len(resumenes), len(tratamientos_agendables) * 7)
        categorias_resumidas = {evento["extendedProps"]["categoria"] for evento in resumenes_categoria}
        self.assertIn(Tratamiento.AgendaCategoria.CONSULTORIO, categorias_resumidas)
        self.assertIn(Tratamiento.AgendaCategoria.NTF, categorias_resumidas)
        self.assertIn(Tratamiento.AgendaCategoria.PRP, categorias_resumidas)

    def test_cancelar_conserva_el_turno_y_libera_su_bloque(self):
        usuario = User.objects.create_user(username="recepcion_cancel", password="secret123")
        grupo, _ = Group.objects.get_or_create(name="Recepcionista")
        usuario.groups.add(grupo)
        self.client.force_login(usuario)
        fecha = timezone.localdate() + timedelta(days=7)
        while fecha.weekday() > 4:
            fecha += timedelta(days=1)
        inicio = timezone.make_aware(
            timezone.datetime.combine(fecha, timezone.datetime.min.time().replace(hour=8))
        )
        turno = Turno.objects.create(
            paciente=self.paciente,
            tratamiento=self.ntf,
            indicacion_medica=self.indicacion,
            fecha_asistencia=inicio,
            estado=Turno.Estado.RESERVADO,
        )

        respuesta = self.client.post(
            reverse("agenda_turno_estado", kwargs={"turno_id": turno.pk}),
            {"estado": Turno.Estado.CANCELADO},
        )

        self.assertRedirects(respuesta, reverse("agenda"))
        turno.refresh_from_db()
        self.assertEqual(turno.estado, Turno.Estado.CANCELADO)
        self.assertTrue(Turno.objects.filter(pk=turno.pk).exists())
        calendario = self.client.get(
            reverse("agenda_disponibilidad_json"),
            {
                "tratamiento": self.ntf.pk,
                "dni": self.paciente.dni,
                "start": fecha.isoformat(),
                "end": (fecha + timedelta(days=1)).isoformat(),
            },
        ).json()
        disponibles = [evento for evento in calendario if evento["extendedProps"].get("disponible")]
        resumen = next(evento for evento in calendario if evento["extendedProps"].get("disponibilidadResumen"))
        cancelados = [evento for evento in calendario if evento["extendedProps"].get("estado") == "Cancelado"]
        self.assertEqual(len(disponibles), 48)
        self.assertEqual(resumen["extendedProps"]["cantidadDisponible"], 48)
        self.assertEqual(len(cancelados), 1)

    def test_finalizar_descuenta_una_sesion_una_sola_vez(self):
        usuario = User.objects.create_user(username="recepcion_finaliza", password="secret123")
        grupo, _ = Group.objects.get_or_create(name="Recepcionista")
        usuario.groups.add(grupo)
        self.client.force_login(usuario)
        plan = PlanPago.objects.create(
            dni=self.paciente,
            tratamiento=self.ntf,
            valor_sesion=100,
            sesiones_total=12,
            metodo_pago="efectivo",
        )
        fecha = timezone.now() + timedelta(days=8)
        turno = Turno.objects.create(
            paciente=self.paciente,
            tratamiento=self.ntf,
            plan=plan,
            indicacion_medica=self.indicacion,
            fecha_asistencia=fecha,
            estado=Turno.Estado.ASIGNADO,
        )

        self.client.post(
            reverse("agenda_turno_estado", kwargs={"turno_id": turno.pk}),
            {"estado": Turno.Estado.FINALIZADO},
        )
        self.client.post(
            reverse("agenda_turno_estado", kwargs={"turno_id": turno.pk}),
            {"estado": Turno.Estado.AUSENTE},
        )

        plan.refresh_from_db()
        turno.refresh_from_db()
        self.assertEqual(plan.sesiones_consumidas, 1)
        self.assertEqual(turno.estado, Turno.Estado.FINALIZADO)