import unicodedata

from django.core.exceptions import PermissionDenied


def puede_ver_secciones_administrativas(usuario):
    if usuario.is_superuser:
        return True

    grupos = {
        "".join(
            caracter
            for caracter in unicodedata.normalize("NFKD", nombre or "").lower()
            if not unicodedata.combining(caracter)
        )
        for nombre in usuario.groups.values_list("name", flat=True)
    }
    return "medico" not in grupos


def exigir_acceso_secciones_administrativas(usuario):
    if not puede_ver_secciones_administrativas(usuario):
        raise PermissionDenied
