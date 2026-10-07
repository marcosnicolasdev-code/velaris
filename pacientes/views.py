from datetime import date, datetime, time, timedelta

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.utils import timezone
from django.http import JsonResponse
from django.db import transaction
from django.urls import reverse

import unicodedata
import re

from .models import Paciente, Evolucion, Turno
from .forms import (
    PacienteForm,
    TurnoForm,
    AgendarTurnoForm,
    SeleccionarPacienteTurnoForm,
    TratamientoIndicadoForm,
)
from usuarios.models import Profesional
from tratamientos.models import Tratamiento, PlanPago

# READ  (El Listado y Buscador)
@login_required
def paciente_lista(request):
    q = request.GET.get("q", "").strip()
    pacientes = Paciente.objects.all()

    if q:
        busqueda = "".join(
            caracter
            for caracter in unicodedata.normalize("NFD", q.lower())
            if unicodedata.category(caracter) != "Mn"
        )

        pacientes = [
            paciente for paciente in pacientes
            if busqueda in unicodedata.normalize(
                "NFD", paciente.dni.lower()
            ).encode("ascii", "ignore").decode()
            or busqueda in unicodedata.normalize(
                "NFD", paciente.nombre_paciente.lower()
            ).encode("ascii", "ignore").decode()
            or busqueda in unicodedata.normalize(
                "NFD", paciente.apellido_paciente.lower()
            ).encode("ascii", "ignore").decode()
        ]

    return render(
        request,
        "pacientes/paciente_lista.html",
        {"pacientes": pacientes, "q": q},
    )


# READesto
@login_required
def paciente_detalle(request, dni):
    paciente = get_object_or_404(Paciente, dni=dni)
    turnos = Turno.objects.filter(paciente=paciente).order_by("-fecha_asistencia")
    planes = PlanPago.objects.filter(dni=paciente).order_by("-fecha_inicio_tratamiento", "-id_plan")
    plan_actual = planes.filter(estado="activo").first() or planes.first()
    historia = paciente.get_historia_clinica()
    evoluciones = (
        historia.evoluciones
        .select_related("profesional__usuario", "usuario", "turno")
        .order_by("-fecha_evolucion")
    )
    for evolucion in evoluciones:
        lineas = evolucion.descripcion.splitlines()
        etiquetas_clinicas = {
            "Pte.:",
            "Pte. se acerca por:",
            "Antecedentes:",
            "Examen físico:",
            "Se le indica:",
        }
        evolucion.primera_linea = next(
            (
                linea.strip()
                for linea in lineas
                if linea.strip()
                and linea.strip() not in etiquetas_clinicas
                and not linea.strip().startswith("Pte.")
            ),
            "Sin descripción.",
        )
    grupos_clinicos = {"medico", "enfermero", "instrumentador"}
    grupos_recepcion = {"recepcionista", "administrativo"}
    nombres_grupos = {
        unicodedata.normalize("NFKD", nombre or "")
        .encode("ascii", "ignore")
        .decode("ascii")
        .strip()
        .lower()
        for nombre in request.user.groups.values_list("name", flat=True)
    }
    puede_cobrar_plan = (
        request.user.is_superuser
        or bool(grupos_recepcion & nombres_grupos)
        or "ceo" in nombres_grupos
    )
    tratamientos_indicados = Tratamiento.objects.filter(
        requiere_plan=True,
        evoluciones_indicacion__historia_clinica__paciente=paciente,
    ).distinct()
    planes_activos = PlanPago.objects.filter(dni=paciente, estado="activo")
    tratamientos_sin_plan = [
        tratamiento
        for tratamiento in tratamientos_indicados
        if not planes_activos.filter(tratamiento=tratamiento).exists()
    ]
    puede_crear_medica = (
        request.user.is_superuser
        or bool(grupos_clinicos & nombres_grupos)
    )
    puede_asignar_tratamiento = (
        request.user.is_superuser
        or bool(grupos_clinicos & nombres_grupos)
    )
    puede_crear_privada = (
        not puede_crear_medica
        and (
            request.user.is_superuser
            or bool(grupos_recepcion & nombres_grupos)
        )
    )

    return render(
        request,
        "pacientes/paciente_detalle.html",
        {
            "paciente": paciente,
            "turnos": turnos,
            "historia": historia,
            "evoluciones": evoluciones,
            "planes": planes,
            "plan_actual": plan_actual,
            "puede_crear_privada": puede_crear_privada,
            "puede_crear_medica": puede_crear_medica,
            "puede_asignar_tratamiento": puede_asignar_tratamiento,
            "puede_cobrar_plan": puede_cobrar_plan,
            "tratamientos_sin_plan": tratamientos_sin_plan,
        },
    )


@login_required
def evolucion_detalle(request, dni, evolucion_id):
    paciente = get_object_or_404(Paciente, dni=dni)
    evolucion = get_object_or_404(
        Evolucion.objects.select_related("profesional__usuario", "usuario"),
        id=evolucion_id,
        historia_clinica__paciente=paciente,
    )
    secciones = []
    etiquetas = [
        "Pte.:",
        "Pte. realiza:",
        "Antecedentes:",
        "Examen físico:",
        "Se le indica:",
    ]
    texto = re.sub(
        r"^Pte\.(?: se acerca por| refiere):",
        "Pte.:",
        evolucion.descripcion,
        count=1,
        flags=re.MULTILINE,
    )
    for posicion, etiqueta in enumerate(etiquetas):
        inicio = texto.find(etiqueta)
        if inicio == -1:
            continue
        contenido_inicio = inicio + len(etiqueta)
        contenido_fin = len(texto)
        if posicion + 1 < len(etiquetas):
            siguiente_inicio = texto.find(etiquetas[posicion + 1], contenido_inicio)
            if siguiente_inicio != -1:
                contenido_fin = siguiente_inicio
        secciones.append(
            {
                "etiqueta": etiqueta,
                "contenido": texto[contenido_inicio:contenido_fin].strip(),
            }
        )
    return render(
        request,
        "pacientes/evolucion_detalle.html",
        {
            "paciente": paciente,
            "evolucion": evolucion,
            "secciones": secciones,
        },
    )


# CREATE se usa el patrón GET/POST Sirve tanto para mostrar el formulario vacío como para guardar los datos cuando la recepcionista le da al botón "Guardar"
@login_required
def paciente_crear(request):
    if request.method == "POST":
        form = PacienteForm(request.POST)

        if form.is_valid():
            paciente = form.save()
            return redirect("paciente_detalle", dni=paciente.dni)
    else:
        form = PacienteForm()

    return render(
        request,
        "pacientes/paciente_form.html",
        {"form": form},
    )


# UPDATE  Es casi idéntico al de crear: usa instance=paciente para saber a quién estamos editando y precargar sus datos en los casilleros.
@login_required
def paciente_editar(request, dni):
    paciente = get_object_or_404(Paciente, dni=dni)
    if request.method == "POST":
        form = PacienteForm(request.POST, instance=paciente)
        if form.is_valid():
            form.save()
            return redirect("paciente_detalle", dni=paciente.dni)
    else:
        form = PacienteForm(instance=paciente)
    return render(request, "pacientes/paciente_form.html", {"form": form})


# DELETE
@login_required
def paciente_borrar(request, dni):
    paciente = get_object_or_404(Paciente, dni=dni)
    if request.method == "POST":
        paciente.delete()
        return redirect("paciente_lista")
    return render(request, "pacientes/paciente_confirmar.html", {"paciente": paciente})

#Agendar turno desde la lista de ptes.
@login_required
def agendar_turno(request, dni):
    if not _puede_gestionar_agenda(request.user):
        raise PermissionDenied
    paciente = get_object_or_404(Paciente, dni=dni)

    return render(
        request,
        "pacientes/agenda_provisoria.html",
        {"paciente": paciente},
    )

#vista de “crear evolución” del paciente
@login_required
def evolucion_crear(request, dni):
    es_recepcionista = request.user.groups.filter(name="Recepcionista").exists()
    if not (request.user.is_superuser or es_recepcionista):
        raise PermissionDenied

    paciente = get_object_or_404(Paciente, dni=dni)
    historia = paciente.get_historia_clinica()

    if request.method == "POST":
        fecha = timezone.localdate()
        descripcion = request.POST.get("descripcion", "").strip()

        Evolucion.objects.create(
            historia_clinica=historia,
            profesional=None,
            usuario=request.user,
            tipo=Evolucion.Tipo.PRIVADA,
            fecha_evolucion=fecha,
            resumen="",
            descripcion=descripcion,
        )
        return redirect("paciente_detalle", dni=paciente.dni)

    return render(
        request,
        "pacientes/evolucion_form.html",
        {
            "paciente": paciente,
            "historia": historia,
        },
    )

@login_required
def evolucion_profesional_crear(request, dni):
    grupos_clinicos = {"Médico", "Enfermero", "Instrumentador"}
    es_clinico = request.user.groups.filter(name__in=grupos_clinicos).exists()
    grupos_descripcion_simple = {"Enfermero", "Instrumentador"}
    usa_descripcion_simple = request.user.groups.filter(
        name__in=grupos_descripcion_simple
    ).exists()
    puede_indicar_tratamiento = (
        request.user.is_superuser
        or request.user.groups.filter(name="Médico").exists()
    )
    profesional = getattr(request.user, "profesional", None)
    if profesional is None and not es_clinico:
        raise PermissionDenied

    paciente = get_object_or_404(Paciente, dni=dni)
    historia = paciente.get_historia_clinica()

    if request.method == "POST":
        indicacion_form = TratamientoIndicadoForm(request.POST)
        if puede_indicar_tratamiento and not usa_descripcion_simple and not indicacion_form.is_valid():
            return render(
                request,
                "pacientes/evolucion_profesional_form.html",
                {
                    "paciente": paciente,
                    "indicacion_form": indicacion_form,
                    "puede_indicar_tratamiento": puede_indicar_tratamiento,
                },
            )
        fecha = timezone.localdate()
        if usa_descripcion_simple:
            tipo = request.POST.get("tipo", Evolucion.Tipo.NTF)
            contenido = request.POST.get("descripcion", "").strip()
            descripcion = f"Pte. realiza:\n{contenido}".strip()
            numero_sesion = None
        else:
            tipo = request.POST.get("tipo", Evolucion.Tipo.PRIVADA)
            numero_sesion = None
            motivo = request.POST.get("motivo", "").strip()
            antecedentes = request.POST.get("antecedentes", "").strip()
            examen_fisico = request.POST.get("examen_fisico", "").strip()
            se_indica = request.POST.get("se_indica", "").strip()
            tratamiento_indicado = (
                indicacion_form.cleaned_data["tratamiento_indicado"]
                if puede_indicar_tratamiento
                else None
            )
            descripcion = (
                f"Pte.:\n{motivo}\n\n"
                f"Antecedentes:\n{antecedentes}\n\n"
                f"Examen físico:\n{examen_fisico}\n\n"
                f"Se le indica:\n{se_indica}"
            )

        Evolucion.objects.create(
            historia_clinica=historia,
            profesional=profesional,
            tratamiento_indicado=tratamiento_indicado if not usa_descripcion_simple else None,
            usuario=request.user,
            tipo=tipo,
            fecha_evolucion=fecha,
            numero_sesion=numero_sesion,
            resumen="",
            descripcion=descripcion,
        )
        return redirect("paciente_detalle", dni=paciente.dni)

    return render(
        request,
        "pacientes/evolucion_simple_form.html"
        if usa_descripcion_simple
        else "pacientes/evolucion_profesional_form.html",
        {
            "paciente": paciente,
            "indicacion_form": TratamientoIndicadoForm(),
            "puede_indicar_tratamiento": puede_indicar_tratamiento,
        },
    )

#CRUD TURNOS

#CREATE
@login_required
def turno_crear(request, dni):
    if not _puede_gestionar_agenda(request.user):
        raise PermissionDenied
    paciente = get_object_or_404(Paciente, dni=dni)
    if request.method == "POST":
        form = AgendarTurnoForm(request.POST, paciente=paciente)
        if form.is_valid():
            turno = form.save(commit=False)
            turno.paciente = paciente
            turno.indicacion_medica = form.cleaned_data.get("indicacion_medica")
            turno.plan = form.cleaned_data.get("plan")
            turno.save()
            return redirect("agenda")
    else:
        form = AgendarTurnoForm(paciente=paciente)
    return render(request, "pacientes/turno_form.html", {"paciente": paciente, "form": form})

@login_required
def agendar_turno(request, dni):
    if not _puede_gestionar_agenda(request.user):
        raise PermissionDenied
    paciente = get_object_or_404(Paciente, dni=dni)
    if request.method == "POST":
        form = AgendarTurnoForm(request.POST, paciente=paciente)
        if form.is_valid():
            turno = form.save(commit=False)
            turno.paciente = paciente
            turno.indicacion_medica = form.cleaned_data.get("indicacion_medica")
            turno.plan = form.cleaned_data.get("plan")
            turno.save()
            return redirect("agenda")
    else:
        form = AgendarTurnoForm(paciente=paciente)
    return render(request, "pacientes/agendar_turno.html", {"form": form, "paciente": paciente})

#READ
@login_required
def turno_lista(request, dni):
    paciente = get_object_or_404(Paciente, dni=dni)
    turnos = Turno.objects.filter(paciente=paciente)
    return render(request, "pacientes/turno_lista.html", {"paciente": paciente, "turnos": turnos})

#UPDATE
@login_required
def turno_editar(request, dni, turno_id):
    if not _puede_gestionar_agenda(request.user):
        raise PermissionDenied
    paciente = get_object_or_404(Paciente, dni=dni)
    turno = get_object_or_404(Turno, id=turno_id, paciente=paciente)
    if turno.estado not in {Turno.Estado.RESERVADO, Turno.Estado.ASIGNADO}:
        return redirect("agenda")
    if request.method == "POST":
        form = AgendarTurnoForm(request.POST, instance=turno, paciente=paciente)
        if form.is_valid():
            turno = form.save(commit=False)
            turno.indicacion_medica = form.cleaned_data.get("indicacion_medica")
            turno.plan = form.cleaned_data.get("plan")
            turno.save()
            return redirect("agenda")
    else:
        form = AgendarTurnoForm(instance=turno, paciente=paciente)
    return render(
        request,
        "pacientes/agendar_turno.html",
        {"paciente": paciente, "form": form, "edicion": True, "turno": turno},
    )

@login_required
def finalizar_turno(request, dni, turno_id):
    if not _puede_gestionar_agenda(request.user):
        raise PermissionDenied
    paciente = get_object_or_404(Paciente, dni=dni)
    turno = get_object_or_404(Turno, id=turno_id, paciente=paciente)

    if request.method == "POST":
        with transaction.atomic():
            if turno.estado not in {Turno.Estado.RESERVADO, Turno.Estado.ASIGNADO}:
                return redirect("agenda")
            turno.estado = Turno.Estado.FINALIZADO
            turno.save(update_fields=["estado"])

            # si el turno es de un plan, descontar una sesión
            if turno.plan:
                plan = turno.plan
                plan.sesiones_consumidas += 1
                if plan.sesiones_consumidas >= plan.sesiones_total:
                    plan.estado = "completado"
                plan.save()

        return redirect("paciente_detalle", dni=paciente.dni)

    return render(request, "pacientes/finalizar_turno.html", {"turno": turno, "paciente": paciente})

#DELETE
@login_required
def turno_borrar(request, dni, turno_id):
    if not _puede_gestionar_agenda(request.user):
        raise PermissionDenied
    paciente = get_object_or_404(Paciente, dni=dni)
    turno = get_object_or_404(Turno, id=turno_id, paciente=paciente)
    if request.method == "POST":
        if turno.estado in {Turno.Estado.RESERVADO, Turno.Estado.ASIGNADO}:
            turno.estado = Turno.Estado.CANCELADO
            turno.save(update_fields=["estado"])
        return redirect("agenda")
    return render(
        request,
        "pacientes/finalizar_turno.html",
        {"paciente": paciente, "turno": turno, "cancelacion": True},
    )

#CRUD AGENDA

@login_required
def agenda(request):
    if not _puede_gestionar_agenda(request.user):
        raise PermissionDenied
    return render(request, "pacientes/agenda.html")


@login_required
def nuevo_turno_agenda(request):
    if not _puede_gestionar_agenda(request.user):
        raise PermissionDenied
    busqueda = request.GET.get("q", "").strip()
    pacientes = Paciente.objects.none()
    if busqueda:
        termino = unicodedata.normalize("NFKD", busqueda.lower()).encode("ascii", "ignore").decode("ascii")
        pacientes = [
            paciente
            for paciente in Paciente.objects.order_by("apellido_paciente", "nombre_paciente")
            if termino in paciente.dni.lower()
            or termino in unicodedata.normalize(
                "NFKD", f"{paciente.nombre_paciente} {paciente.apellido_paciente}".lower()
            ).encode("ascii", "ignore").decode("ascii")
        ]

    return render(
        request,
        "pacientes/nuevo_turno_agenda.html",
        {"pacientes": pacientes, "busqueda": busqueda},
    )


@login_required
def turnos_json(request):
    if not _puede_gestionar_agenda(request.user):
        raise PermissionDenied
    categoria = request.GET.get("categoria", "")
    turnos = Turno.objects.select_related("paciente", "tratamiento")
    if categoria and categoria != "todas":
        turnos = turnos.filter(tratamiento__agenda_categoria=categoria)
    eventos = []
    for turno in turnos:
        color = _color_estado_turno(turno.estado)
        nombre = f"{turno.paciente.apellido_paciente}, {turno.paciente.nombre_paciente}"
        eventos.append({
            "id": turno.pk,
            "title": f"{nombre} · {turno.get_estado_display()}",
            "start": turno.fecha_asistencia.isoformat(),
            "end": (turno.fecha_asistencia + turno.tratamiento.duracion_tratamiento).isoformat(),
            "backgroundColor": color,
            "borderColor": color,
            "extendedProps": {
                "dni": turno.paciente.dni,
                "nombre": turno.paciente.nombre_paciente,
                "apellido": turno.paciente.apellido_paciente,
                "telefono": turno.paciente.telefono,
                "prestacion": turno.tratamiento.nombre_tratamiento,
                "estado": turno.get_estado_display(),
                "estadoCodigo": turno.estado,
                "nota": turno.nota,
                "editarUrl": reverse("turno_editar", kwargs={"dni": turno.paciente.dni, "turno_id": turno.pk}),
                "estadoUrl": reverse("agenda_turno_estado", kwargs={"turno_id": turno.pk}),
                "editable": turno.estado in {Turno.Estado.RESERVADO, Turno.Estado.ASIGNADO},
            },
        })
    return JsonResponse (eventos, safe=False)


def _puede_gestionar_agenda(usuario):
    grupos = {
        unicodedata.normalize("NFKD", nombre or "")
        .encode("ascii", "ignore")
        .decode("ascii")
        .strip()
        .lower()
        for nombre in usuario.groups.values_list("name", flat=True)
    }
    return usuario.is_superuser or bool(grupos & {"recepcionista", "ceo"})


def _color_estado_turno(estado):
    return {
        Turno.Estado.RESERVADO: "#d79b16",
        Turno.Estado.ASIGNADO: "#247a52",
        Turno.Estado.FINALIZADO: "#3667a6",
        Turno.Estado.AUSENTE: "#bd4a43",
        Turno.Estado.CANCELADO: "#6c757d",
    }.get(estado, "#3667a6")


@login_required
def agenda_disponibilidad_json(request):
    if not _puede_gestionar_agenda(request.user):
        raise PermissionDenied
    try:
        desde = date.fromisoformat(request.GET["start"][:10])
        hasta = date.fromisoformat(request.GET["end"][:10])
    except (KeyError, ValueError):
        return JsonResponse({"error": "Se requiere un rango de fechas válido."}, status=400)

    tratamiento_id = request.GET.get("tratamiento") or request.GET.get("treatment")
    dni = request.GET.get("dni")
    paciente = get_object_or_404(Paciente, dni=dni) if dni else None
    turno_actual_id = request.GET.get("turno")

    if tratamiento_id:
        tratamiento = get_object_or_404(Tratamiento, pk=tratamiento_id)
        if tratamiento.agenda_categoria != Tratamiento.AgendaCategoria.CONSULTORIO:
            if not paciente or not Evolucion.objects.filter(
                historia_clinica__paciente=paciente,
                tratamiento_indicado=tratamiento,
            ).exists():
                raise PermissionDenied

        turnos_agenda = list(
            Turno.objects.select_related("tratamiento")
            .filter(
                tratamiento__agenda_categoria=tratamiento.agenda_categoria,
                fecha_asistencia__date__gte=desde,
                fecha_asistencia__date__lt=hasta,
            )
        )
        if turno_actual_id and turno_actual_id.isdigit():
            turnos_agenda = [turno for turno in turnos_agenda if str(turno.pk) != turno_actual_id]
        ocupados = [
            turno for turno in turnos_agenda
            if turno.estado in {Turno.Estado.RESERVADO, Turno.Estado.ASIGNADO}
        ]
        eventos = []
        fecha_actual = desde
        duracion = tratamiento.duracion_tratamiento
        categoria = tratamiento.agenda_categoria
        while fecha_actual < hasta:
            dia = fecha_actual.weekday()
            if categoria == Tratamiento.AgendaCategoria.MTC:
                inicios = [time(8), time(14)] if dia < 5 else []
                es_dia_agenda = dia < 5
            else:
                if categoria in {Tratamiento.AgendaCategoria.NTF, Tratamiento.AgendaCategoria.PRP}:
                    apertura, cierre = (time(8), time(20)) if dia < 5 else (time(9), time(17)) if dia == 5 else (None, None)
                else:
                    apertura, cierre = (time(8), time(20)) if dia < 5 else (None, None)
                es_dia_agenda = apertura is not None
                inicios = []
                if apertura:
                    cursor = datetime.combine(fecha_actual, apertura)
                    fin_jornada = datetime.combine(fecha_actual, cierre)
                    paso = duracion
                    while cursor + duracion <= fin_jornada:
                        inicios.append(cursor.time())
                        cursor += paso

            libres_dia = 0
            for inicio_hora in inicios:
                inicio = timezone.make_aware(datetime.combine(fecha_actual, inicio_hora), timezone.get_current_timezone())
                fin = inicio + duracion
                if inicio <= timezone.now():
                    continue
                choca = any(
                    inicio < turno.fecha_asistencia + turno.tratamiento.duracion_tratamiento
                    and turno.fecha_asistencia < fin
                    for turno in ocupados
                )
                if not choca:
                    libres_dia += 1
                    eventos.append({
                        "title": f"Disponible · {inicio.strftime('%H:%M')}",
                        "start": inicio.isoformat(),
                        "end": fin.isoformat(),
                        "backgroundColor": "#dcefe4",
                        "borderColor": "#77aa89",
                        "textColor": "#24583a",
                        "extendedProps": {"disponible": True},
                    })
            if es_dia_agenda:
                eventos.append({
                    "title": f"{libres_dia} disponibles",
                    "start": fecha_actual.isoformat(),
                    "allDay": True,
                    "backgroundColor": "transparent",
                    "borderColor": "transparent",
                    "textColor": "#24583a",
                    "extendedProps": {
                        "disponible": False,
                        "disponibilidadResumen": True,
                        "cantidadDisponible": libres_dia,
                    },
                })
            fecha_actual += timedelta(days=1)

        for turno in turnos_agenda:
            if turno.fecha_asistencia.date() < desde or turno.fecha_asistencia.date() >= hasta:
                continue
            fin = turno.fecha_asistencia + turno.tratamiento.duracion_tratamiento
            color = _color_estado_turno(turno.estado)
            eventos.append({
                "title": (
                    f"{turno.paciente.apellido_paciente}, {turno.paciente.nombre_paciente} · "
                    f"{turno.tratamiento.nombre_tratamiento} · {turno.get_estado_display()}"
                ),
                "start": turno.fecha_asistencia.isoformat(),
                "end": fin.isoformat(),
                "backgroundColor": color,
                "borderColor": color,
                "extendedProps": {
                    "disponible": False,
                    "estado": turno.get_estado_display(),
                    "dni": turno.paciente.dni,
                    "nombre": turno.paciente.nombre_paciente,
                    "apellido": turno.paciente.apellido_paciente,
                    "telefono": turno.paciente.telefono,
                    "prestacion": turno.tratamiento.nombre_tratamiento,
                    "nota": turno.nota,
                },
            })

        return JsonResponse(eventos, safe=False)

    categorias = [
        Tratamiento.AgendaCategoria.CONSULTORIO,
        Tratamiento.AgendaCategoria.MTC,
        Tratamiento.AgendaCategoria.NTF,
        Tratamiento.AgendaCategoria.PRP,
    ]
    etiquetas = {
        Tratamiento.AgendaCategoria.CONSULTORIO: "Consultorio",
        Tratamiento.AgendaCategoria.MTC: "MTC",
        Tratamiento.AgendaCategoria.NTF: "NTF",
        Tratamiento.AgendaCategoria.PRP: "PRP",
    }
    eventos = []
    fecha_actual = desde
    while fecha_actual < hasta:
        for categoria in categorias:
            tratamientos = Tratamiento.objects.filter(agenda_categoria=categoria)
            if not tratamientos.exists():
                continue
            libres_dia = 0
            for tratamiento in tratamientos:
                duracion = tratamiento.duracion_tratamiento
                dia = fecha_actual.weekday()
                if categoria == Tratamiento.AgendaCategoria.MTC:
                    inicios = [time(8), time(14)] if dia < 5 else []
                elif categoria in {Tratamiento.AgendaCategoria.NTF, Tratamiento.AgendaCategoria.PRP}:
                    if dia < 5:
                        apertura, cierre = time(8), time(20)
                    elif dia == 5:
                        apertura, cierre = time(9), time(17)
                    else:
                        apertura, cierre = None, None
                    inicios = []
                    if apertura:
                        cursor = datetime.combine(fecha_actual, apertura)
                        fin_jornada = datetime.combine(fecha_actual, cierre)
                        while cursor + duracion <= fin_jornada:
                            inicios.append(cursor.time())
                            cursor += timedelta(minutes=int(duracion.total_seconds() // 60))
                else:
                    if dia < 5:
                        apertura, cierre = time(8), time(20)
                    else:
                        apertura, cierre = None, None
                    inicios = []
                    if apertura:
                        cursor = datetime.combine(fecha_actual, apertura)
                        fin_jornada = datetime.combine(fecha_actual, cierre)
                        while cursor + duracion <= fin_jornada:
                            inicios.append(cursor.time())
                            cursor += duracion
                for inicio_hora in inicios:
                    inicio = timezone.make_aware(datetime.combine(fecha_actual, inicio_hora), timezone.get_current_timezone())
                    fin = inicio + duracion
                    if inicio <= timezone.now():
                        continue
                    ocupados = Turno.objects.filter(
                        tratamiento__agenda_categoria=categoria,
                        estado__in=[Turno.Estado.RESERVADO, Turno.Estado.ASIGNADO],
                        fecha_asistencia__lt=fin,
                        fecha_asistencia__gte=inicio,
                    )
                    if not ocupados.exists():
                        libres_dia += 1
            eventos.append({
                "title": f"{etiquetas[categoria]}: {libres_dia} disponibles",
                "start": fecha_actual.isoformat(),
                "allDay": True,
                "backgroundColor": "transparent",
                "borderColor": "transparent",
                "textColor": "#24583a",
                "extendedProps": {
                    "disponible": False,
                    "resumenCategoria": True,
                    "categoria": categoria,
                    "cantidadDisponible": libres_dia,
                },
            })
        fecha_actual += timedelta(days=1)
    return JsonResponse(eventos, safe=False)


@login_required
def agenda_turno_estado(request, turno_id):
    if not _puede_gestionar_agenda(request.user):
        raise PermissionDenied
    turno = get_object_or_404(Turno, pk=turno_id)
    if turno.estado not in {Turno.Estado.RESERVADO, Turno.Estado.ASIGNADO}:
        return redirect("agenda")
    if request.method == "POST":
        estado = request.POST.get("estado")
        estados_permitidos = {
            Turno.Estado.RESERVADO,
            Turno.Estado.ASIGNADO,
            Turno.Estado.FINALIZADO,
            Turno.Estado.AUSENTE,
            Turno.Estado.CANCELADO,
        }
        if estado in estados_permitidos:
            with transaction.atomic():
                turno = Turno.objects.select_for_update().get(pk=turno_id)
                estado_anterior = turno.estado
                turno.estado = estado
                turno.save(update_fields=["estado"])
                if estado == Turno.Estado.FINALIZADO and estado_anterior != Turno.Estado.FINALIZADO and turno.plan_id:
                    plan = PlanPago.objects.select_for_update().get(pk=turno.plan_id)
                    if plan.sesiones_consumidas < plan.sesiones_total:
                        plan.sesiones_consumidas += 1
                        if plan.sesiones_consumidas >= plan.sesiones_total:
                            plan.estado = "completado"
                        plan.save(update_fields=["sesiones_consumidas", "estado"])
    return redirect("agenda")

