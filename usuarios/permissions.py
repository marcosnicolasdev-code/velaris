import unicodedata

from django.core.exceptions import PermissionDenied


def puede_ver_secciones_administrativas(usuario):
    if usuario.is_superuser:
        return True

    grupos = _grupos_normalizados(usuario)
    return "medico" not in grupos


def puede_ver_opcion_menu(usuario, opcion):
    if usuario.is_superuser:
        return True

    grupos = _grupos_normalizados(usuario)
    if "administrativo" in grupos and opcion in {
        "nuevo_paciente",
        "nuevo_tratamiento",
        "turnos",
        "nuevo_profesional",
    }:
        return False
    if opcion == "nuevo_profesional" and grupos & {"recepcionista", "medico"}:
        return False
    return True


def _grupos_normalizados(usuario):
    return {
        "".join(
            caracter
            for caracter in unicodedata.normalize("NFKD", nombre or "").lower()
            if not unicodedata.combining(caracter)
        )
        for nombre in usuario.groups.values_list("name", flat=True)
    }


def exigir_acceso_secciones_administrativas(usuario):
    if not puede_ver_secciones_administrativas(usuario):
        raise PermissionDenied
