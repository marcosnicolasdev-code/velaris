from django import template

from usuarios.permissions import (
    puede_ver_opcion_menu,
    puede_ver_secciones_administrativas,
)


register = template.Library()


@register.filter
def puede_ver_secciones_administrativas_tag(usuario):
    return puede_ver_secciones_administrativas(usuario)


@register.filter
def puede_ver_opcion_menu_tag(usuario, opcion):
    return puede_ver_opcion_menu(usuario, opcion)
