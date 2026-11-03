from datetime import timedelta

from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from pacientes.forms import AgendarTurnoForm
from pacientes.models import HistoriaClinica, Paciente, Evolucion, Turno
from pacientes.views import _filtrar_pacientes_por_busqueda
from tratamientos.models import PlanPago, Tratamiento
from usuarios.models import Profesional


class PatientSearchTests(TestCase):
    def setUp(self):
        self.paciente = Paciente.objects.create(
            dni="12345678",
            nombre_paciente="Juan Carlos",
            apellido_paciente="Pérez Gómez",
            fecha_nacimiento="1990-05-10",
            correo_electronico="juan@example.com",
            telefono="3415551234",
        )

    def test_busca_nombre_y_apellido_juntos_en_cualquier_orden(self):
        pacientes = Paciente.objects.all()

        self.assertEqual(
            _filtrar_pacientes_por_busqueda(pacientes, "Juan Pérez"),
            [self.paciente],
        )
        self.assertEqual(
            _filtrar_pacientes_por_busqueda(pacientes, "Perez Juan"),
            [self.paciente],
        )


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
    def test_usuario_administrativo_puede_ingresar_a_agenda(self):
        usuario = User.objects.create_user(username="administrativo_agenda", password="secret123")
        grupo, _ = Group.objects.get_or_create(name="Administrativo")
        usuario.groups.add(grupo)
        self.client.force_login(usuario)

        respuesta = self.client.get(reverse("agenda"))

        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "Agenda de turnos")

    def test_medico_puede_ingresar_a_agenda(self):
        usuario = User.objects.create_user(username="medico_agenda", password="secret123")
        grupo, _ = Group.objects.get_or_create(name="Médico")
        usuario.groups.add(grupo)
        self.client.force_login(usuario)

        respuesta = self.client.get(reverse("agenda"))

        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "Agenda de turnos")

    def test_usuario_sin_rol_no_puede_ingresar_a_agenda(self):
        usuario = User.objects.create_user(username="sin_rol_agenda", password="secret123")
        self.client.force_login(usuario)

        respuesta = self.client.get(reverse("agenda"))

        self.assertEqual(respuesta.status_code, 403)

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

    def test_agendar_turno_no_pide_plan_ni_nota_y_guarda_estado(self):
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

        pantalla = self.client.get(reverse("agendar_turno", kwargs={"dni": paciente.dni}))
        self.assertNotContains(pantalla, "Nota administrativa")
        self.assertNotContains(pantalla, "id_nota")

        respuesta = self.client.post(
            reverse("agendar_turno", kwargs={"dni": paciente.dni}),
            {
                "tratamiento": tratamiento.pk,
                "fecha_asistencia": f"{fecha.isoformat()}T10:00",
                "estado": Turno.Estado.RESERVADO,
            },
        )

        self.assertRedirects(respuesta, reverse("agenda"))
        turno = Turno.objects.get(paciente=paciente)
        self.assertIsNone(turno.plan)
        self.assertEqual(turno.estado, Turno.Estado.RESERVADO)
        self.assertEqual(turno.nota, "")

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
        self.assertEqual(turno.nota, "Nota inicial")


class EvolutionDetailTests(TestCase):
    def test_historia_clinica_muestra_el_texto_de_paciente_refiere(self):
        usuario = User.objects.create_user(username="doctor_historia")
        self.client.force_login(usuario)
        paciente = Paciente.objects.create(
            dni="12345679",
            nombre_paciente="Ana",
            apellido_paciente="Pérez",
            fecha_nacimiento="1990-05-10",
            domicilio="Calle 123",
            localidad="Rosario",
            correo_electronico="ana.historia@example.com",
            telefono="3415551234",
            obra_social="OSDE",
            sexo="Femenino",
        )
        Evolucion.objects.create(
            historia_clinica=paciente.get_historia_clinica(),
            tipo=Evolucion.Tipo.PRIMERA_CONSULTA,
            fecha_evolucion=timezone.localdate(),
            descripcion=(
                "Paciente refiere:\nDolor lumbar desde hace una semana\n\n"
                "Antecedentes:\nSin antecedentes relevantes"
            ),
        )

        respuesta = self.client.get(
            reverse("paciente_detalle", kwargs={"dni": paciente.dni})
        )

        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(
            respuesta,
            "Paciente refiere: Dolor lumbar desde hace una semana",
        )

    def test_detalle_muestra_el_contenido_de_paciente_refiere(self):
        usuario = User.objects.create_user(username="doctor_evolucion")
        self.client.force_login(usuario)
        paciente = Paciente.objects.create(
            dni="12345678",
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
        evolucion = Evolucion.objects.create(
            historia_clinica=paciente.get_historia_clinica(),
            tipo=Evolucion.Tipo.PRIMERA_CONSULTA,
            fecha_evolucion=timezone.localdate(),
            descripcion=(
                "Paciente refiere:\nDolor lumbar desde hace una semana\n\n"
                "Antecedentes:\nSin antecedentes relevantes"
            ),
        )

        respuesta = self.client.get(
            reverse(
                "evolucion_detalle",
                kwargs={"dni": paciente.dni, "evolucion_id": evolucion.pk},
            )
        )

        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "Paciente refiere:")
        self.assertContains(respuesta, "Dolor lumbar desde hace una semana")
        self.assertEqual(
            respuesta.context["secciones"][0]["contenido"],
            "Dolor lumbar desde hace una semana",
        )


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

    def test_prp_no_se_agenda_con_ntf_en_curso_sin_plan(self):
        self.ntf.sesion_tratamiento = 12
        self.ntf.save(update_fields=["sesion_tratamiento"])
        prp = Tratamiento.objects.create(
            nombre_tratamiento="PRP de prueba",
            duracion_tratamiento=timedelta(minutes=15),
            sesion_tratamiento=12,
            requiere_plan=True,
            agenda_categoria=Tratamiento.AgendaCategoria.PRP,
        )
        Evolucion.objects.create(
            historia_clinica=self.paciente.get_historia_clinica(),
            tratamiento_indicado=prp,
            fecha_evolucion=timezone.localdate(),
            descripcion="Indica PRP",
        )
        Turno.objects.create(
            paciente=self.paciente,
            tratamiento=self.ntf,
            fecha_asistencia=timezone.now() - timedelta(days=1),
            estado=Turno.Estado.FINALIZADO,
        )

        form = AgendarTurnoForm(
            {
                "tratamiento": prp.pk,
                "fecha_asistencia": self.fecha_semana(10, 15),
                "estado": Turno.Estado.RESERVADO,
                "nota": "",
            },
            paciente=self.paciente,
        )

        self.assertFalse(form.is_valid())
        self.assertIn("tratamiento", form.errors)

    def test_prp_no_se_agenda_mientras_haya_un_plan_ntf_activo(self):
        prp = Tratamiento.objects.create(
            nombre_tratamiento="PRP de prueba",
            duracion_tratamiento=timedelta(minutes=15),
            sesion_tratamiento=12,
            requiere_plan=True,
            agenda_categoria=Tratamiento.AgendaCategoria.PRP,
        )
        Evolucion.objects.create(
            historia_clinica=self.paciente.get_historia_clinica(),
            tratamiento_indicado=prp,
            fecha_evolucion=timezone.localdate(),
            descripcion="Indica PRP",
        )
        PlanPago.objects.create(
            dni=self.paciente,
            tratamiento=self.ntf,
            valor_sesion=100,
            sesiones_total=12,
            metodo_pago="efectivo",
        )

        form = AgendarTurnoForm(
            {
                "tratamiento": prp.pk,
                "fecha_asistencia": self.fecha_semana(10, 15),
                "estado": Turno.Estado.RESERVADO,
                "nota": "",
            },
            paciente=self.paciente,
        )

        self.assertFalse(form.is_valid())
        self.assertIn("tratamiento", form.errors)

    def test_mtc_se_puede_agendar_mientras_ntf_esta_activo(self):
        Evolucion.objects.create(
            historia_clinica=self.paciente.get_historia_clinica(),
            tratamiento_indicado=self.mtc,
            fecha_evolucion=timezone.localdate(),
            descripcion="Indica MTC",
        )
        PlanPago.objects.create(
            dni=self.paciente,
            tratamiento=self.ntf,
            valor_sesion=100,
            sesiones_total=12,
            metodo_pago="efectivo",
        )

        form = AgendarTurnoForm(
            {
                "tratamiento": self.mtc.pk,
                "fecha_asistencia": self.fecha_semana(8),
                "estado": Turno.Estado.RESERVADO,
                "nota": "",
            },
            paciente=self.paciente,
        )

        self.assertTrue(form.is_valid(), form.errors)

    def test_primera_consulta_solo_para_pacientes_sin_turnos_previos(self):
        paciente_nuevo = Paciente.objects.create(
            dni="11223344",
            nombre_paciente="Marina",
            apellido_paciente="Pérez",
            fecha_nacimiento="1995-11-02",
            domicilio="Calle 99",
            localidad="Rosario",
            correo_electronico="marina@example.com",
            telefono="3415551122",
            obra_social="OSDE",
            sexo="Femenino",
        )

        form_nuevo = AgendarTurnoForm(
            {
                "tratamiento": self.consulta.pk,
                "fecha_asistencia": self.fecha_semana(10, 0),
                "estado": Turno.Estado.RESERVADO,
                "nota": "",
            },
            paciente=paciente_nuevo,
        )
        self.assertTrue(form_nuevo.is_valid(), form_nuevo.errors)

        Turno.objects.create(
            paciente=self.paciente,
            tratamiento=self.consulta,
            fecha_asistencia=timezone.now() + timedelta(days=2),
            estado=Turno.Estado.ASIGNADO,
        )

        form_existente = AgendarTurnoForm(
            {
                "tratamiento": self.consulta.pk,
                "fecha_asistencia": self.fecha_semana(11, 0),
                "estado": Turno.Estado.RESERVADO,
                "nota": "",
            },
            paciente=self.paciente,
        )

        self.assertFalse(form_existente.is_valid())
        self.assertIn("tratamiento", form_existente.errors)

    def test_detalle_muestra_historial_y_tratamiento_en_curso_tras_turno_finalizado(self):
        usuario = User.objects.create_user(username="paciente_tratamientos")
        self.client.force_login(usuario)
        self.ntf.sesion_tratamiento = 12
        self.ntf.save(update_fields=["sesion_tratamiento"])
        Turno.objects.create(
            paciente=self.paciente,
            tratamiento=self.ntf,
            indicacion_medica=self.indicacion,
            fecha_asistencia=timezone.now() - timedelta(days=1),
            estado=Turno.Estado.FINALIZADO,
        )

        respuesta = self.client.get(
            reverse("paciente_detalle", kwargs={"dni": self.paciente.dni})
        )

        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "Historial de tratamientos realizados")
        self.assertContains(respuesta, self.ntf.nombre_tratamiento)
        self.assertContains(respuesta, "1 de")
        self.assertContains(respuesta, "12 sesiones realizadas")
        self.assertNotContains(respuesta, "Asignar tratamiento")

    def test_resumen_mtc_muestra_cantidad_y_anios_distintos_en_el_mismo_cuadro(self):
        usuario = User.objects.create_user(username="paciente_mtc_completado")
        self.client.force_login(usuario)
        for fecha_mtc in (
            timezone.datetime(2026, 10, 20, 14, 0),
            timezone.datetime(2023, 10, 20, 14, 0),
            timezone.datetime(2026, 11, 20, 14, 0),
        ):
            Turno.objects.create(
                paciente=self.paciente,
                tratamiento=self.mtc,
                indicacion_medica=self.indicacion,
                fecha_asistencia=timezone.make_aware(fecha_mtc),
                estado=Turno.Estado.FINALIZADO,
            )

        respuesta = self.client.get(
            reverse("paciente_detalle", kwargs={"dni": self.paciente.dni})
        )

        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "MTC realizado")
        self.assertContains(respuesta, "MTC 3: (2026-2023)")
        self.assertNotContains(respuesta, "MTC realizados</h3>")

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
        self.assertFalse(resumenes)
        self.assertTrue(resumenes_categoria)
        self.assertEqual(len(resumenes_categoria), 4 * 7)
        categorias_resumidas = {evento["extendedProps"]["categoria"] for evento in resumenes_categoria}
        self.assertIn(Tratamiento.AgendaCategoria.CONSULTORIO, categorias_resumidas)
        self.assertIn(Tratamiento.AgendaCategoria.NTF, categorias_resumidas)
        self.assertIn(Tratamiento.AgendaCategoria.PRP, categorias_resumidas)
        self.assertTrue(all("disponibles" not in evento["title"] for evento in resumenes_categoria))

    def test_resumen_consultorio_muestra_24_horarios_compartidos(self):
        usuario = User.objects.create_user(username="recepcion_consultorio", password="test1234")
        grupo, _ = Group.objects.get_or_create(name="Recepcionista")
        usuario.groups.add(grupo)
        self.client.force_login(usuario)
        fecha = timezone.localdate() + timedelta(days=7)
        while fecha.weekday() > 4:
            fecha += timedelta(days=1)

        respuesta = self.client.get(
            reverse("agenda_disponibilidad_json"),
            {"start": fecha.isoformat(), "end": (fecha + timedelta(days=1)).isoformat()},
        )

        self.assertEqual(respuesta.status_code, 200)
        resumen_consultorio = next(
            evento for evento in respuesta.json()
            if evento["extendedProps"].get("resumenCategoria")
            and evento["extendedProps"]["categoria"] == Tratamiento.AgendaCategoria.CONSULTORIO
        )
        prestaciones_consultorio = Tratamiento.objects.filter(
            agenda_categoria=Tratamiento.AgendaCategoria.CONSULTORIO
        )
        self.assertTrue({
            "Primera consulta",
            "Nueva evaluación",
            "Control de medicación",
            "Control de PRP",
            "Control de Nutrifol",
        }.issubset(set(prestaciones_consultorio.values_list("nombre_tratamiento", flat=True))))
        self.assertEqual(resumen_consultorio["extendedProps"]["cantidadDisponible"], 24)
        self.assertEqual(resumen_consultorio["title"], "Consultorio: 24")

    def test_consultorio_en_agenda_crea_un_solo_evento_generico_por_bloque(self):
        usuario = User.objects.create_user(username="recepcion_consultorio_bloques", password="test1234")
        grupo, _ = Group.objects.get_or_create(name="Recepcionista")
        usuario.groups.add(grupo)
        self.client.force_login(usuario)
        fecha = timezone.localdate() + timedelta(days=7)
        while fecha.weekday() > 4:
            fecha += timedelta(days=1)

        respuesta = self.client.get(
            reverse("agenda_disponibilidad_json"),
            {
                "categoria": Tratamiento.AgendaCategoria.CONSULTORIO,
                "modo": "agenda",
                "start": fecha.isoformat(),
                "end": (fecha + timedelta(days=1)).isoformat(),
            },
        )

        self.assertEqual(respuesta.status_code, 200)
        eventos = respuesta.json()
        self.assertEqual(len(eventos), 24)
        self.assertEqual({evento["title"] for evento in eventos}, {"Consultorio"})
        self.assertEqual(len({evento["start"] for evento in eventos}), 24)
        self.assertTrue(all(
            evento["extendedProps"]["categoria"] == Tratamiento.AgendaCategoria.CONSULTORIO
            and evento["extendedProps"]["consultorioGeneral"]
            and "tratamientoId" not in evento["extendedProps"]
            for evento in eventos
        ))

    def test_turno_ocupado_reduce_un_horario_compartido_de_consultorio(self):
        usuario = User.objects.create_user(username="recepcion_consultorio_ocupado", password="test1234")
        grupo, _ = Group.objects.get_or_create(name="Recepcionista")
        usuario.groups.add(grupo)
        self.client.force_login(usuario)
        fecha = timezone.localdate() + timedelta(days=7)
        while fecha.weekday() > 4:
            fecha += timedelta(days=1)
        inicio = timezone.make_aware(
            timezone.datetime.combine(fecha, timezone.datetime.min.time().replace(hour=8))
        )
        Turno.objects.create(
            paciente=self.paciente,
            tratamiento=self.consulta,
            fecha_asistencia=inicio,
            estado=Turno.Estado.ASIGNADO,
        )

        respuesta = self.client.get(
            reverse("agenda_disponibilidad_json"),
            {"start": fecha.isoformat(), "end": (fecha + timedelta(days=1)).isoformat()},
        )

        resumen_consultorio = next(
            evento for evento in respuesta.json()
            if evento["extendedProps"].get("resumenCategoria")
            and evento["extendedProps"]["categoria"] == Tratamiento.AgendaCategoria.CONSULTORIO
        )
        self.assertEqual(resumen_consultorio["extendedProps"]["cantidadDisponible"], 23)

    def test_agenda_filtrada_muestra_resumenes_y_horarios_de_categoria(self):
        usuario = User.objects.create_user(username="recepcion_agenda_filtrada", password="secret123")
        grupo, _ = Group.objects.get_or_create(name="Recepcionista")
        usuario.groups.add(grupo)
        self.client.force_login(usuario)
        fecha = timezone.localdate() + timedelta(days=7)
        while fecha.weekday() > 4:
            fecha += timedelta(days=1)
        parametros = {
            "categoria": Tratamiento.AgendaCategoria.NTF,
            "start": fecha.isoformat(),
            "end": (fecha + timedelta(days=7)).isoformat(),
        }

        respuesta_resumen = self.client.get(reverse("agenda_disponibilidad_json"), parametros)

        self.assertEqual(respuesta_resumen.status_code, 200)
        resumenes = [
            evento for evento in respuesta_resumen.json()
            if evento["extendedProps"].get("resumenCategoria")
        ]
        self.assertTrue(resumenes)
        self.assertTrue(all(
            evento["extendedProps"]["categoria"] == Tratamiento.AgendaCategoria.NTF
            for evento in resumenes
        ))
        parametros["modo"] = "agenda"

        respuesta = self.client.get(reverse("agenda_disponibilidad_json"), parametros)

        self.assertEqual(respuesta.status_code, 200)
        eventos = respuesta.json()
        self.assertTrue(eventos)
        self.assertTrue(all(evento["extendedProps"].get("disponible") for evento in eventos))
        self.assertTrue(all(
            evento["extendedProps"]["categoria"] == Tratamiento.AgendaCategoria.NTF
            for evento in eventos
        ))

    def test_busqueda_filtra_por_tratamiento_excepto_consultorio(self):
        usuario = User.objects.create_user(username="recepcion_busqueda_turno", password="secret123")
        grupo, _ = Group.objects.get_or_create(name="Recepcionista")
        usuario.groups.add(grupo)
        self.client.force_login(usuario)
        paciente_sin_indicacion = Paciente.objects.create(
            dni="99887766",
            nombre_paciente="Mateo",
            apellido_paciente="Gómez",
            fecha_nacimiento="1988-04-12",
            correo_electronico="mateo@example.com",
            telefono="3415559988",
        )

        respuesta_ntf = self.client.get(
            reverse("agenda_pacientes_disponibles_json"),
            {"tratamiento": self.ntf.pk, "q": "Sofia"},
        )
        self.assertEqual(respuesta_ntf.status_code, 200)
        self.assertEqual([paciente["dni"] for paciente in respuesta_ntf.json()], [self.paciente.dni])

        respuesta_consulta = self.client.get(
            reverse("agenda_pacientes_disponibles_json"),
            {"tratamiento": self.consulta.pk, "q": "Mateo"},
        )
        self.assertEqual(respuesta_consulta.status_code, 200)
        self.assertEqual(respuesta_consulta.json()[0]["dni"], paciente_sin_indicacion.dni)

    def test_asignacion_valida_tratamiento_y_permite_consulta_sin_indicacion(self):
        usuario = User.objects.create_user(username="recepcion_asigna_turno", password="secret123")
        grupo, _ = Group.objects.get_or_create(name="Recepcionista")
        usuario.groups.add(grupo)
        self.client.force_login(usuario)
        paciente_sin_indicacion = Paciente.objects.create(
            dni="88776655",
            nombre_paciente="Lucía",
            apellido_paciente="Méndez",
            fecha_nacimiento="1992-09-20",
            correo_electronico="lucia@example.com",
            telefono="3415558877",
        )
        fecha_asistencia = self.fecha_semana(10)

        respuesta_ntf = self.client.post(
            reverse("agenda_asignar_turno_disponible"),
            {
                "dni": paciente_sin_indicacion.dni,
                "tratamiento": self.ntf.pk,
                "fecha_asistencia": fecha_asistencia,
            },
        )
        self.assertEqual(respuesta_ntf.status_code, 400)
        self.assertFalse(Turno.objects.filter(paciente=paciente_sin_indicacion).exists())

        respuesta_consulta = self.client.post(
            reverse("agenda_asignar_turno_disponible"),
            {
                "dni": paciente_sin_indicacion.dni,
                "tratamiento": self.consulta.pk,
                "fecha_asistencia": fecha_asistencia,
            },
        )
        self.assertEqual(respuesta_consulta.status_code, 201, respuesta_consulta.content)
        turno_consulta = Turno.objects.get(paciente=paciente_sin_indicacion)
        self.assertEqual(turno_consulta.tratamiento, self.consulta)
        self.assertEqual(turno_consulta.estado, Turno.Estado.ASIGNADO)

        respuesta_ntf_elegible = self.client.post(
            reverse("agenda_asignar_turno_disponible"),
            {
                "dni": self.paciente.dni,
                "tratamiento": self.ntf.pk,
                "fecha_asistencia": fecha_asistencia,
            },
        )
        self.assertEqual(respuesta_ntf_elegible.status_code, 201, respuesta_ntf_elegible.content)
        turno_ntf = Turno.objects.get(paciente=self.paciente)
        self.assertEqual(turno_ntf.tratamiento, self.ntf)
        self.assertEqual(turno_ntf.indicacion_medica, self.indicacion)

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
        eventos_turnos = self.client.get(
            reverse("turnos_json"),
            {"start": fecha.isoformat(), "end": (fecha + timedelta(days=1)).isoformat()},
        ).json()
        self.assertFalse(any(evento["id"] == turno.pk for evento in eventos_turnos))
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

        respuesta = self.client.post(
            reverse("agenda_turno_estado", kwargs={"turno_id": turno.pk}),
            {"estado": Turno.Estado.PRESENTE},
        )
        self.assertRedirects(respuesta, reverse("agenda"))
        plan.refresh_from_db()
        turno.refresh_from_db()
        self.assertEqual(plan.sesiones_consumidas, 0)
        self.assertEqual(turno.estado, Turno.Estado.PRESENTE)

        self.client.post(
            reverse("agenda_turno_estado", kwargs={"turno_id": turno.pk}),
            {"estado": Turno.Estado.FINALIZADO},
        )
        self.client.post(
            reverse("agenda_turno_estado", kwargs={"turno_id": turno.pk}),
            {"estado": Turno.Estado.CANCELADO},
        )

        plan.refresh_from_db()
        turno.refresh_from_db()
        self.assertEqual(plan.sesiones_consumidas, 1)
        self.assertEqual(turno.estado, Turno.Estado.FINALIZADO)

    def test_presente_aparece_en_curso_y_habilita_completar_desde_historia(self):
        usuario = User.objects.create_user(username="recepcion_presente")
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
        turno = Turno.objects.create(
            paciente=self.paciente,
            tratamiento=self.ntf,
            plan=plan,
            indicacion_medica=self.indicacion,
            fecha_asistencia=timezone.now() + timedelta(days=8),
            estado=Turno.Estado.ASIGNADO,
        )

        detalle = self.client.get(
            reverse("paciente_detalle", kwargs={"dni": self.paciente.dni})
        )
        self.assertContains(detalle, "Presente")
        self.assertContains(detalle, "<th>Fecha y hora</th>")
        self.assertContains(
            detalle,
            timezone.localtime(turno.fecha_asistencia).strftime("%d/%m/%Y, %H:%M"),
        )
        self.assertNotContains(detalle, "Completado</button>")

        respuesta = self.client.post(
            reverse(
                "turno_estado_paciente",
                kwargs={"dni": self.paciente.dni, "turno_id": turno.pk},
            ),
            {"estado": Turno.Estado.PRESENTE},
        )

        self.assertRedirects(
            respuesta,
            f"{reverse('paciente_detalle', kwargs={'dni': self.paciente.dni})}#turnos-panel",
        )
        turno.refresh_from_db()
        plan.refresh_from_db()
        self.assertEqual(turno.estado, Turno.Estado.PRESENTE)
        self.assertEqual(plan.sesiones_consumidas, 0)
        detalle = self.client.get(
            reverse("paciente_detalle", kwargs={"dni": self.paciente.dni})
        )
        self.assertContains(detalle, "12 restantes")
        self.assertContains(detalle, "Completado")

    def test_presente_sin_plan_inicia_tratamiento_en_curso(self):
        usuario = User.objects.create_user(username="recepcion_presente_sin_plan")
        grupo, _ = Group.objects.get_or_create(name="Recepcionista")
        usuario.groups.add(grupo)
        self.client.force_login(usuario)
        turno = Turno.objects.create(
            paciente=self.paciente,
            tratamiento=self.ntf,
            indicacion_medica=self.indicacion,
            fecha_asistencia=timezone.now() + timedelta(days=8),
            estado=Turno.Estado.ASIGNADO,
        )

        self.client.post(
            reverse("agenda_turno_estado", kwargs={"turno_id": turno.pk}),
            {"estado": Turno.Estado.PRESENTE},
        )

        detalle = self.client.get(
            reverse("paciente_detalle", kwargs={"dni": self.paciente.dni})
        )
        self.assertContains(detalle, "NTF")
        self.assertContains(detalle, "12 sesiones realizadas")
        self.assertContains(detalle, "12 restantes")

    def test_no_se_puede_completar_sin_marcar_presente(self):
        usuario = User.objects.create_user(username="recepcion_sin_presente")
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
        turno = Turno.objects.create(
            paciente=self.paciente,
            tratamiento=self.ntf,
            plan=plan,
            indicacion_medica=self.indicacion,
            fecha_asistencia=timezone.now() + timedelta(days=8),
            estado=Turno.Estado.ASIGNADO,
        )

        respuesta = self.client.post(
            reverse("agenda_turno_estado", kwargs={"turno_id": turno.pk}),
            {"estado": Turno.Estado.FINALIZADO},
        )

        self.assertRedirects(respuesta, reverse("agenda"))
        turno.refresh_from_db()
        plan.refresh_from_db()
        self.assertEqual(turno.estado, Turno.Estado.ASIGNADO)
        self.assertEqual(plan.sesiones_consumidas, 0)