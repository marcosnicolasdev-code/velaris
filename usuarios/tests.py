from django.contrib.auth.models import Group, User
from django.test import TestCase


class PermisosGrupoTests(TestCase):
    def test_recepcionista_tiene_permiso_de_admin_para_pacientes(self):
        grupo = Group.objects.get_or_create(name="Recepcionista")[0]
        usuario = User.objects.create_user(username="recepcionista_test", password="secret123")

        usuario.groups.add(grupo)
        usuario.refresh_from_db()

        self.assertTrue(usuario.is_staff)
        self.assertTrue(usuario.has_perm("pacientes.view_paciente"))
        self.assertTrue(usuario.has_perm("pacientes.change_paciente"))
