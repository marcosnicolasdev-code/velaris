from datetime import datetime, timezone as datetime_timezone
from unittest.mock import patch

from django.contrib.auth.models import Group, User
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from usuarios.models import Caja, MovimientoCaja


class PermisosGrupoTests(TestCase):
    def test_recepcionista_tiene_permiso_de_admin_para_pacientes(self):
        grupo = Group.objects.get_or_create(name="Recepcionista")[0]
        usuario = User.objects.create_user(username="recepcionista_test", password="secret123")

        usuario.groups.add(grupo)
        usuario.refresh_from_db()

        self.assertTrue(usuario.is_staff)
        self.assertTrue(usuario.has_perm("pacientes.view_paciente"))
        self.assertTrue(usuario.has_perm("pacientes.change_paciente"))


class CajaMovimientoTests(TestCase):
    def setUp(self):
        self.usuario = User.objects.create_user(username="recepcionista_caja")
        self.caja = Caja.objects.create(usuario=self.usuario)
        self.client.force_login(self.usuario)

    def test_registra_egreso_en_la_caja_del_usuario(self):
        respuesta = self.client.post(
            reverse("registrar_movimiento"),
            {
                "tipo_movimiento": "egreso",
                "categoria_movimiento": "pago_servicio",
                "descripcion_movimiento": "Servicio de prueba",
                "importe_movimiento": "12500",
            },
        )

        self.assertRedirects(respuesta, reverse("caja_movimientos"))
        movimiento = MovimientoCaja.objects.get()
        self.assertEqual(movimiento.caja, self.caja)
        self.assertEqual(movimiento.tipo_movimiento, "egreso")
        self.assertEqual(movimiento.importe_movimiento, 12500)

    @override_settings(TIME_ZONE="America/Argentina/Buenos_Aires")
    def test_resumen_usa_fecha_local_cerca_de_medianoche(self):
        MovimientoCaja.objects.create(
            caja=self.caja,
            tipo_movimiento="ingreso",
            categoria_movimiento="venta",
            importe_movimiento=20000,
        )
        MovimientoCaja.objects.create(
            caja=self.caja,
            tipo_movimiento="egreso",
            categoria_movimiento="pago_servicio",
            importe_movimiento=5000,
        )
        MovimientoCaja.objects.filter(caja=self.caja).update(
            fecha_movimiento=datetime(2026, 11, 4, 2, 2, tzinfo=datetime_timezone.utc)
        )

        ahora_utc = datetime(2026, 11, 4, 2, 5, tzinfo=datetime_timezone.utc)
        with timezone.override("America/Argentina/Buenos_Aires"):
            with patch("django.utils.timezone.now", return_value=ahora_utc):
                respuesta = self.client.get(reverse("caja_movimientos"))

        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.context["ingresos"], 20000)
        self.assertEqual(respuesta.context["egresos"], 5000)
        self.assertEqual(respuesta.context["saldo"], 15000)
        self.assertEqual(respuesta.context["movimientos"].count(), 2)
