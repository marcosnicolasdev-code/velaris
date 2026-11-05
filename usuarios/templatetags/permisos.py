from django import template

from usuarios.permissions import puede_ver_secciones_administrativas


register = template.Library()


@register.filter
def puede_ver_secciones_administrativas_tag(usuario):
    return puede_ver_secciones_administrativas(usuario)
