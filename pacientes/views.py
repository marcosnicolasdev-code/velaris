from datetime import date, datetime, time, timedelta

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
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
    puede_agendar_tratamiento,
)
from usuarios.models import Profesional
from tratamientos.models import Tratamiento, PlanPago

# READ  (El Listado y Buscador)
def _normalizar_busqueda(texto):
    return "".join(
        caracter
        for caracter in unicodedata.normalize("NFD", texto.lower())
        if unicodedata.category(caracter) != "Mn"
    ).encode("ascii", "ignore").decode("ascii")


def _filtrar_pacientes_por_busqueda(pacientes, consulta):
    busqueda = " ".join(_normalizar_busqueda(consulta).split())
    if not busqueda:
        return pacientes

    def coincide(paciente):
        nombre = _normalizar_busqueda(paciente.nombre_paciente)
        apellido = _normalizar_busqueda(paciente.apellido_paciente)
        palabras = busqueda.split()
        nombre_y_apellido = (
            all(palabra in f"{nombre} {apellido}" for palabra in palabras)
            and any(palabra in nombre for palabra in palabras)
            and any(palabra in apellido for palabra in palabras)
        )
        return (
            busqueda in _normalizar_busqueda(paciente.dni)
            or busqueda in nombre
            or busqueda in apellido
            or nombre_y_apellido
        )

    return [paciente for paciente in pacientes if coincide(paciente)]


def _turno_puede_corregir(turno, ahora):
    return (
        turno.estado in {Turno.Estado.PRESENTE, Turno.Estado.FINALIZADO}
        and turno.fecha_asistencia > ahora
    )


def _turno_estado_editable(turno, ahora):
    return turno.estado in {
        Turno.Estado.RESERVADO,
        Turno.Estado.ASIGNADO,
        Turno.Estado.PRESENTE,
    } or (
        turno.estado == Turno.Estado.FINALIZADO
        and turno.fecha_asistencia > ahora
    )


@login_required
def paciente_lista(request):
    q = request.GET.get("q", "").strip()
    pacientes = _filtrar_pacientes_por_busqueda(Paciente.objects.all(), q)

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
    ahora = timezone.now()
    for turno in turnos:
        turno.estado_color = _color_estado_turno(turno.estado)
        turno.puede_corregir_estado = _turno_puede_corregir(turno, ahora)
        turno.puede_gestionar_estado = _turno_estado_editable(turno, ahora)
    planes = PlanPago.objects.filter(dni=paciente).select_related("tratamiento").order_by(
        "-fecha_inicio_tratamiento", "-id_plan"
    )
    tratamientos_en_curso = [
        {
            "tratamiento": plan.tratamiento,
            "sesiones_realizadas": plan.sesiones_consumidas,
            "sesiones_total": plan.sesiones_total,
            "sesiones_restantes": plan.sesiones_restantes,
        }
        for plan in planes
        if plan.estado == "activo"
        and plan.sesiones_consumidas < plan.sesiones_total
        and (
            plan.sesiones_consumidas > 0
            or Turno.objects.filter(
                plan=plan,
                estado=Turno.Estado.PRESENTE,
            ).exists()
        )
    ]
    turnos_tratamiento_realizados = (
        Turno.objects.filter(
            paciente=paciente,
            estado=Turno.Estado.FINALIZADO,
        )
        .exclude(tratamiento__agenda_categoria=Tratamiento.AgendaCategoria.CONSULTORIO)
        .select_related("tratamiento")
        .order_by("-fecha_asistencia")
    )
    mtc_realizados = turnos_tratamiento_realizados.filter(
        tratamiento__agenda_categoria=Tratamiento.AgendaCategoria.MTC
    )
    mtc_realizados_lista = list(mtc_realizados)
    mtc_realizados_cantidad = len(mtc_realizados_lista)
    mtc_realizados_anios = "-".join(
        str(anio)
        for anio in sorted(
            {
                timezone.localtime(turno.fecha_asistencia).year
                for turno in mtc_realizados_lista
            },
            reverse=True,
        )
    )
    tratamientos_con_plan_activo = {
        plan.tratamiento_id for plan in planes if plan.estado == "activo"
    }
    tratamientos_sin_plan_realizados = (
        turnos_tratamiento_realizados.filter(plan__isnull=True)
        .values_list("tratamiento_id", flat=True)
        .distinct()
    )
    tratamientos_sin_plan_presentes = set(Turno.objects.filter(
        paciente=paciente,
        plan__isnull=True,
        estado=Turno.Estado.PRESENTE,
    ).exclude(
        tratamiento__agenda_categoria=Tratamiento.AgendaCategoria.CONSULTORIO
    ).values_list("tratamiento_id", flat=True))
    for tratamiento in Tratamiento.objects.filter(
        pk__in=set(tratamientos_sin_plan_realizados) | set(tratamientos_sin_plan_presentes)
    ):
        sesiones_realizadas = turnos_tratamiento_realizados.filter(
            tratamiento=tratamiento,
            plan__isnull=True,
        ).count()
        if (
            tratamiento.pk not in tratamientos_con_plan_activo
            and sesiones_realizadas < tratamiento.sesion_tratamiento
            and (
                sesiones_realizadas
                or tratamiento.pk in tratamientos_sin_plan_presentes
            )
        ):
            tratamientos_en_curso.append(
                {
                    "tratamiento": tratamiento,
                    "sesiones_realizadas": sesiones_realizadas,
                    "sesiones_total": tratamiento.sesion_tratamiento,
                    "sesiones_restantes": tratamiento.sesion_tratamiento - sesiones_realizadas,
                }
            )
    historia = paciente.get_historia_clinica()
    evoluciones = (
        historia.evoluciones
        .select_related("profesional__usuario", "usuario", "turno")
        .order_by("-fecha_evolucion", "-created_at")
    )
    for evolucion in evoluciones:
        etiquetas_clinicas = {
            "Pte.:",
            "Pte. se acerca por:",
            "Antecedentes:",
            "Examen físico:",
            "Se le indica:",
        }
        refiere = re.search(
            r"^(?:Paciente refiere|Pte\.(?:\s*(?:se acerca por|refiere))?)\s*:\s*"
            r"(.*?)(?=^\s*(?:Antecedentes|Examen físico|Se le indica|Pte\. realiza)\s*:|\Z)",
            evolucion.descripcion,
            flags=re.MULTILINE | re.DOTALL | re.IGNORECASE,
        )
        if refiere:
            evolucion.primera_linea = (
                f"Paciente refiere: {refiere.group(1).strip()}".strip()
            )
        else:
            evolucion.primera_linea = next(
                (
                    linea.strip()
                    for linea in evolucion.descripcion.splitlines()
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
    tratamientos_sin_plan = []
    for tratamiento in tratamientos_indicados:
        categoria_opuesta = {
            Tratamiento.AgendaCategoria.NTF: Tratamiento.AgendaCategoria.PRP,
            Tratamiento.AgendaCategoria.PRP: Tratamiento.AgendaCategoria.NTF,
        }.get(tratamiento.agenda_categoria)
        hay_plan_activo_mismo = planes_activos.filter(
            tratamiento=tratamiento
        ).exists()
        hay_plan_activo_opuesto = (
            planes_activos.filter(
                tratamiento__agenda_categoria=categoria_opuesta
            ).exists()
            if categoria_opuesta
            else False
        )
        if not hay_plan_activo_mismo and not hay_plan_activo_opuesto:
            tratamientos_sin_plan.append(tratamiento)
    puede_crear_medica = (
        request.user.is_superuser
        or bool(grupos_clinicos & nombres_grupos)
    )
    puede_gestionar_turnos = _puede_gestionar_agenda(request.user)
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
            "tratamientos_en_curso": tratamientos_en_curso,
            "turnos_tratamiento_realizados": turnos_tratamiento_realizados,
            "mtc_realizados_cantidad": mtc_realizados_cantidad,
            "mtc_realizados_anios": mtc_realizados_anios,
            "puede_crear_privada": puede_crear_privada,
            "puede_crear_medica": puede_crear_medica,
            "puede_gestionar_turnos": puede_gestionar_turnos,
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
        "Paciente refiere:",
        "Pte. realiza:",
        "Antecedentes:",
        "Examen físico:",
        "Se le indica:",
    ]
    texto = re.sub(
        r"^(?:Paciente refiere|Pte\.?\s*(?:se acerca por|refiere)):",
        "Paciente refiere:",
        evolucion.descripcion,
        count=1,
        flags=re.MULTILINE,
    )
    etiquetas_encontradas = []
    for etiqueta in etiquetas:
        inicio = texto.find(etiqueta)
        if inicio != -1:
            etiquetas_encontradas.append((inicio, etiqueta))
    etiquetas_encontradas.sort()
    for posicion, (inicio, etiqueta) in enumerate(etiquetas_encontradas):
        contenido_inicio = inicio + len(etiqueta)
        contenido_fin = (
            etiquetas_encontradas[posicion + 1][0]
            if posicion + 1 < len(etiquetas_encontradas)
            else len(texto)
        )
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
    
    # Permitir si es superusuario o está en un grupo clínico
    if not (request.user.is_superuser or es_clinico):
        raise PermissionDenied
    
    grupos_descripcion_simple = {"Enfermero", "Instrumentador"}
    usa_descripcion_simple = request.user.groups.filter(
        name__in=grupos_descripcion_simple
    ).exists()
    puede_indicar_tratamiento = (
        request.user.is_superuser
        or request.user.groups.filter(name="Médico").exists()
    )
    profesional = getattr(request.user, "profesional", None)

    paciente = get_object_or_404(Paciente, dni=dni)
    historia = paciente.get_historia_clinica()

    if request.method == "POST":
        indicacion_form = TratamientoIndicadoForm(request.POST) if puede_indicar_tratamiento else TratamientoIndicadoForm()
        
        # Validar formulario de tratamiento si aplica
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
            tratamiento_indicado = None
        else:
            tipo = request.POST.get("tipo", Evolucion.Tipo.PRIVADA)
            numero_sesion = None
            motivo = request.POST.get("motivo", "").strip()
            antecedentes = request.POST.get("antecedentes", "").strip()
            examen_fisico = request.POST.get("examen_fisico", "").strip()
            se_indica = request.POST.get("se_indica", "").strip()
            tratamiento_indicado = (
                indicacion_form.cleaned_data.get("tratamiento_indicado")
                if puede_indicar_tratamiento and indicacion_form.is_valid()
                else None
            )
            descripcion = (
                f"Paciente refiere:\n{motivo}\n\n"
                f"Antecedentes:\n{antecedentes}\n\n"
                f"Examen físico:\n{examen_fisico}\n\n"
                f"Se le indica:\n{se_indica}"
            )
            
            # Validar compatibilidad entre tipo de evolución y tratamiento indicado
            if tratamiento_indicado:
                tipo_lower = tipo.lower()
                
                # Verificar si el paciente tiene planes activos
                planes_activos = PlanPago.objects.filter(dni=paciente, estado="activo")
                plan_prp_activo = planes_activos.filter(
                    tratamiento__agenda_categoria=Tratamiento.AgendaCategoria.PRP
                ).first()
                plan_ntf_activo = planes_activos.filter(
                    tratamiento__agenda_categoria=Tratamiento.AgendaCategoria.NTF
                ).first()
                
                # Es evolución de CONTROL (seguimiento), se permite indicar tratamiento opuesto
                es_control = "control_" in tipo_lower
                
                # NTF (sin ser control) no puede asignar tratamiento PRP
                if "ntf" in tipo_lower and not es_control and tratamiento_indicado.agenda_categoria == Tratamiento.AgendaCategoria.PRP:
                    return render(
                        request,
                        "pacientes/evolucion_profesional_form.html",
                        {
                            "paciente": paciente,
                            "indicacion_form": indicacion_form,
                            "puede_indicar_tratamiento": puede_indicar_tratamiento,
                            "error": "No se puede asignar un tratamiento PRP en una evolución NTF.",
                        },
                    )
                # PRP (sin ser control) no puede asignar tratamiento NTF
                if "prp" in tipo_lower and not es_control and tratamiento_indicado.agenda_categoria == Tratamiento.AgendaCategoria.NTF:
                    return render(
                        request,
                        "pacientes/evolucion_profesional_form.html",
                        {
                            "paciente": paciente,
                            "indicacion_form": indicacion_form,
                            "puede_indicar_tratamiento": puede_indicar_tratamiento,
                            "error": "No se puede asignar un tratamiento NTF en una evolución PRP.",
                        },
                    )
                
                # Si es evolución simple (NTF/PRP sin "control_"), valida que no esté haciendo el tratamiento opuesto
                if not es_control:
                    # Si es evolución NTF y está haciendo PRP, no permite
                    if "ntf" in tipo_lower and plan_prp_activo:
                        return render(
                            request,
                            "pacientes/evolucion_profesional_form.html",
                            {
                                "paciente": paciente,
                                "indicacion_form": indicacion_form,
                                "puede_indicar_tratamiento": puede_indicar_tratamiento,
                                "error": "El paciente está haciendo PRP. No se puede crear una evolución NTF mientras esté en PRP.",
                            },
                        )
                    
                    # Si es evolución PRP y está haciendo NTF, no permite
                    if "prp" in tipo_lower and plan_ntf_activo:
                        return render(
                            request,
                            "pacientes/evolucion_profesional_form.html",
                            {
                                "paciente": paciente,
                                "indicacion_form": indicacion_form,
                                "puede_indicar_tratamiento": puede_indicar_tratamiento,
                                "error": "El paciente está haciendo NTF. No se puede crear una evolución PRP mientras esté en NTF.",
                            },
                        )

        Evolucion.objects.create(
            historia_clinica=historia,
            profesional=profesional,
            tratamiento_indicado=tratamiento_indicado,
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
    return redirect(f"{reverse('agenda')}?paciente={paciente.dni}")

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


def _actualizar_estado_turno(turno_id, estado):
    with transaction.atomic():
        turno = Turno.objects.select_for_update().get(pk=turno_id)
        puede_corregir = turno.fecha_asistencia > timezone.now()
        estados_pendientes = {Turno.Estado.RESERVADO, Turno.Estado.ASIGNADO}
        transiciones = {
            Turno.Estado.PRESENTE: estados_pendientes,
            Turno.Estado.CANCELADO: estados_pendientes | {Turno.Estado.PRESENTE},
            Turno.Estado.FINALIZADO: {Turno.Estado.PRESENTE},
        }
        estados_corregibles = {Turno.Estado.PRESENTE, Turno.Estado.FINALIZADO}
        transicion_valida = turno.estado in transiciones.get(estado, set())
        if estado in {Turno.Estado.RESERVADO, Turno.Estado.ASIGNADO}:
            transicion_valida = (
                turno.estado in estados_pendientes
                and turno.estado != estado
            ) or (
                puede_corregir and turno.estado in estados_corregibles
            )
        elif estado == Turno.Estado.CANCELADO and puede_corregir:
            transicion_valida = transicion_valida or turno.estado == Turno.Estado.FINALIZADO
        if not transicion_valida:
            return False

        if turno.estado == Turno.Estado.FINALIZADO and turno.plan_id:
            plan = PlanPago.objects.select_for_update().get(pk=turno.plan_id)
            finalizados = Turno.objects.filter(
                plan=plan,
                estado=Turno.Estado.FINALIZADO,
            ).count()
            if plan.sesiones_consumidas and finalizados <= plan.sesiones_consumidas:
                plan.sesiones_consumidas -= 1
                if plan.estado == "completado" and plan.sesiones_consumidas < plan.sesiones_total:
                    plan.estado = "activo"
                plan.save(update_fields=["sesiones_consumidas", "estado"])

        if estado == Turno.Estado.FINALIZADO and turno.plan_id:
            plan = PlanPago.objects.select_for_update().get(pk=turno.plan_id)
            if plan.sesiones_consumidas < plan.sesiones_total:
                plan.sesiones_consumidas += 1
                if plan.sesiones_consumidas >= plan.sesiones_total:
                    plan.estado = "completado"
                plan.save(update_fields=["sesiones_consumidas", "estado"])

        turno.estado = estado
        turno.save(update_fields=["estado"])
        return True


@login_required
def finalizar_turno(request, dni, turno_id):
    if not _puede_gestionar_agenda(request.user):
        raise PermissionDenied
    paciente = get_object_or_404(Paciente, dni=dni)
    turno = get_object_or_404(Turno, id=turno_id, paciente=paciente)

    if request.method == "POST":
        if not _actualizar_estado_turno(turno_id, Turno.Estado.FINALIZADO):
            messages.error(request, "Para completar el turno, primero marcá al paciente como presente.")
        return redirect("paciente_detalle", dni=paciente.dni)

    if turno.estado != Turno.Estado.PRESENTE:
        messages.error(request, "Para completar el turno, primero marcá al paciente como presente.")
        return redirect("paciente_detalle", dni=paciente.dni)
    return render(
        request,
        "pacientes/finalizar_turno.html",
        {"turno": turno, "paciente": paciente, "completado": True},
    )

#DELETE
@login_required
def turno_borrar(request, dni, turno_id):
    if not _puede_gestionar_agenda(request.user):
        raise PermissionDenied
    paciente = get_object_or_404(Paciente, dni=dni)
    turno = get_object_or_404(Turno, id=turno_id, paciente=paciente)
    if request.method == "POST":
        if not _actualizar_estado_turno(turno_id, Turno.Estado.CANCELADO):
            messages.error(request, "No se puede cancelar este turno en su estado actual.")
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
    tratamientos_consultorio = Tratamiento.objects.filter(
        agenda_categoria=Tratamiento.AgendaCategoria.CONSULTORIO,
    ).order_by("nombre_tratamiento")
    paciente_agenda_datos = None
    dni_paciente = request.GET.get("paciente")
    if dni_paciente and not request.GET.get("reagendar"):
        paciente = get_object_or_404(Paciente, dni=dni_paciente)
        paciente_agenda_datos = {
            "dni": paciente.dni,
            "nombre": paciente.nombre_paciente,
            "apellido": paciente.apellido_paciente,
            "telefono": paciente.telefono,
        }
    reagendar_datos = None
    turno_id = request.GET.get("reagendar")
    if turno_id:
        turno = get_object_or_404(
            Turno.objects.select_related("paciente", "tratamiento"),
            pk=turno_id,
            estado__in=[Turno.Estado.RESERVADO, Turno.Estado.ASIGNADO],
        )
        reagendar_datos = {
            "id": turno.pk,
            "dni": turno.paciente.dni,
            "nombre": turno.paciente.nombre_paciente,
            "apellido": turno.paciente.apellido_paciente,
            "tratamientoId": turno.tratamiento_id,
            "prestacion": turno.tratamiento.nombre_tratamiento,
            "categoria": turno.tratamiento.agenda_categoria,
            "estado": turno.estado,
            "fecha": timezone.localtime(turno.fecha_asistencia).date().isoformat(),
        }
    return render(
        request,
        "pacientes/agenda.html",
        {
            "tratamientos_consultorio": tratamientos_consultorio,
            "reagendar_datos": reagendar_datos,
            "paciente_agenda_datos": paciente_agenda_datos,
        },
    )


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
    try:
        desde = date.fromisoformat(request.GET["start"][:10])
        hasta = date.fromisoformat(request.GET["end"][:10])
    except (KeyError, ValueError):
        return JsonResponse({"error": "Se requiere un rango de fechas válido."}, status=400)

    categoria = request.GET.get("categoria", "")
    turnos = Turno.objects.select_related("paciente", "tratamiento").filter(
        fecha_asistencia__date__gte=desde,
        fecha_asistencia__date__lt=hasta,
    ).exclude(estado=Turno.Estado.CANCELADO)
    if categoria and categoria != "todas":
        turnos = turnos.filter(tratamiento__agenda_categoria=categoria)
    eventos = []
    ahora = timezone.now()
    for turno in turnos:
        color = _color_estado_turno(turno.estado)
        nombre = f"{turno.paciente.apellido_paciente}, {turno.paciente.nombre_paciente}"
        eventos.append({
            "id": turno.pk,
            "title": f"{turno.tratamiento.nombre_tratamiento} · {nombre}",
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
                "historiaClinicaUrl": reverse("paciente_detalle", kwargs={"dni": turno.paciente.dni}),
                "reagendarUrl": f"{reverse('agenda')}?reagendar={turno.pk}",
                "estadoUrl": reverse("agenda_turno_estado", kwargs={"turno_id": turno.pk}),
                "editable": _turno_estado_editable(turno, ahora),
                "puedeCorregir": _turno_puede_corregir(turno, ahora),
                    "reagendable": turno.estado in {
                        Turno.Estado.RESERVADO,
                        Turno.Estado.ASIGNADO,
                    },
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
    return (
        usuario.is_superuser
        or usuario.is_staff
        or bool(grupos & {"recepcionista", "administrativo", "medico", "ceo"})
    )


def _color_estado_turno(estado):
    return {
        Turno.Estado.RESERVADO: "#d79b16",
        Turno.Estado.ASIGNADO: "#247a52",
        Turno.Estado.PRESENTE: "#7651a8",
        Turno.Estado.FINALIZADO: "#3667a6",
        Turno.Estado.AUSENTE: "#bd4a43",
        Turno.Estado.CANCELADO: "#6c757d",
    }.get(estado, "#3667a6")


@login_required
def agenda_pacientes_disponibles_json(request):
    if not _puede_gestionar_agenda(request.user):
        raise PermissionDenied

    tratamiento = get_object_or_404(Tratamiento, pk=request.GET.get("tratamiento"))
    consulta = request.GET.get("q", "").strip()
    if not consulta:
        return JsonResponse([], safe=False)

    pacientes = Paciente.objects.order_by("apellido_paciente", "nombre_paciente")
    if tratamiento.agenda_categoria != Tratamiento.AgendaCategoria.CONSULTORIO:
        pacientes_indicados = Evolucion.objects.filter(
            tratamiento_indicado=tratamiento,
        ).values_list("historia_clinica__paciente_id", flat=True)
        pacientes = pacientes.filter(pk__in=pacientes_indicados)

    resultados = _filtrar_pacientes_por_busqueda(pacientes, consulta)[:30]
    if tratamiento.agenda_categoria != Tratamiento.AgendaCategoria.CONSULTORIO:
        resultados = [
            paciente
            for paciente in resultados
            if puede_agendar_tratamiento(paciente, tratamiento)
        ]
    return JsonResponse(
        [
            {
                "dni": paciente.dni,
                "nombre": paciente.nombre_paciente,
                "apellido": paciente.apellido_paciente,
                "telefono": paciente.telefono,
            }
            for paciente in resultados
        ],
        safe=False,
    )


@login_required
def agenda_asignar_turno_disponible(request):
    if not _puede_gestionar_agenda(request.user):
        raise PermissionDenied
    if request.method != "POST":
        return JsonResponse({"error": "Método no permitido."}, status=405)

    paciente = get_object_or_404(Paciente, dni=request.POST.get("dni"))
    tratamiento = get_object_or_404(Tratamiento, pk=request.POST.get("tratamiento"))
    turno_id = request.POST.get("turno")
    turno = None
    if turno_id:
        turno = get_object_or_404(Turno, pk=turno_id, paciente=paciente)
        if turno.estado not in {Turno.Estado.RESERVADO, Turno.Estado.ASIGNADO}:
            return JsonResponse({"error": "Este turno ya no se puede reagendar."}, status=400)
        if turno.tratamiento_id != tratamiento.pk:
            return JsonResponse({"error": "No se puede cambiar la prestación al reagendar."}, status=400)
        estado = turno.estado
    else:
        estado = request.POST.get("estado", Turno.Estado.ASIGNADO)
        if estado not in {Turno.Estado.RESERVADO, Turno.Estado.ASIGNADO}:
            return JsonResponse({"error": "Elegí Reservado o Asignado para el turno."}, status=400)
    indicacion = None
    if not puede_agendar_tratamiento(paciente, tratamiento):
        if tratamiento.agenda_categoria != Tratamiento.AgendaCategoria.CONSULTORIO:
            return JsonResponse(
                {"error": "El tratamiento no está indicado o es incompatible con un tratamiento activo/en curso."},
                status=400,
            )
    if tratamiento.agenda_categoria != Tratamiento.AgendaCategoria.CONSULTORIO:
        indicacion = Evolucion.objects.filter(
            historia_clinica__paciente=paciente,
            tratamiento_indicado=tratamiento,
        ).order_by("-fecha_evolucion", "-id").first()
        if not indicacion:
            return JsonResponse(
                {"error": "El paciente no tiene indicado este tratamiento o cirugía."},
                status=400,
            )

    form = AgendarTurnoForm(
        {
            "tratamiento": tratamiento.pk,
            "fecha_asistencia": request.POST.get("fecha_asistencia", ""),
            "estado": estado,
        },
        instance=turno,
        paciente=paciente,
    )
    if not form.is_valid():
        errores = [str(error) for errores_campo in form.errors.values() for error in errores_campo]
        return JsonResponse({"error": " ".join(errores)}, status=400)

    turno = form.save(commit=False)
    turno.paciente = paciente
    turno.indicacion_medica = (
        form.cleaned_data.get("indicacion_medica", turno.indicacion_medica) or indicacion
    )
    turno.plan = form.cleaned_data.get("plan", turno.plan)
    turno.save()
    return JsonResponse({"ok": True, "turnoId": turno.pk}, status=200 if turno_id else 201)


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
            if not paciente or not puede_agendar_tratamiento(paciente, tratamiento):
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
            if turno.estado in {
                Turno.Estado.RESERVADO,
                Turno.Estado.ASIGNADO,
                Turno.Estado.PRESENTE,
            }
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
                },
            })

        return JsonResponse(eventos, safe=False)

    categorias = [
        Tratamiento.AgendaCategoria.CONSULTORIO,
        Tratamiento.AgendaCategoria.MTC,
        Tratamiento.AgendaCategoria.NTF,
        Tratamiento.AgendaCategoria.PRP,
    ]
    modo_agenda = request.GET.get("modo") == "agenda"
    categoria_agenda = request.GET.get("categoria")
    if categoria_agenda and categoria_agenda != "todas":
        if categoria_agenda not in categorias:
            return JsonResponse({"error": "Se requiere una categoría válida."}, status=400)
        categorias = [categoria_agenda]
    if modo_agenda:
        if not categoria_agenda or categoria_agenda == "todas":
            return JsonResponse({"error": "Se requiere una categoría válida."}, status=400)
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
            tratamientos = Tratamiento.objects.filter(agenda_categoria=categoria).order_by("nombre_tratamiento")
            if not tratamientos.exists():
                continue
            turnos_ocupados_dia = list(
                Turno.objects.select_related("tratamiento").filter(
                    tratamiento__agenda_categoria=categoria,
                    estado__in=[
                        Turno.Estado.RESERVADO,
                        Turno.Estado.ASIGNADO,
                        Turno.Estado.PRESENTE,
                    ],
                    fecha_asistencia__date=fecha_actual,
                )
            )
            libres_categoria = 0
            if categoria == Tratamiento.AgendaCategoria.CONSULTORIO:
                for bloque in range(24):
                    inicio_hora = (datetime.combine(fecha_actual, time(8)) + timedelta(minutes=30 * bloque)).time()
                    inicio = timezone.make_aware(
                        datetime.combine(fecha_actual, inicio_hora),
                        timezone.get_current_timezone(),
                    )
                    fin = inicio + timedelta(minutes=30)
                    ocupado = inicio <= timezone.now() or any(
                        inicio < turno.fecha_asistencia + turno.tratamiento.duracion_tratamiento
                        and turno.fecha_asistencia < fin
                        for turno in turnos_ocupados_dia
                    )
                    if ocupado:
                        continue
                    libres_categoria += 1
                    if modo_agenda:
                        eventos.append({
                            "title": "Consultorio",
                            "start": inicio.isoformat(),
                            "end": fin.isoformat(),
                            "backgroundColor": "#dcefe4",
                            "borderColor": "#77aa89",
                            "textColor": "#24583a",
                            "extendedProps": {
                                "disponible": True,
                                "categoria": categoria,
                                "consultorioGeneral": True,
                                "tratamientoNombre": "Consultorio",
                            },
                        })
                tratamientos = []
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
                libres_dia = 0
                for inicio_hora in inicios:
                    inicio = timezone.make_aware(datetime.combine(fecha_actual, inicio_hora), timezone.get_current_timezone())
                    fin = inicio + duracion
                    if inicio <= timezone.now():
                        continue
                    ocupado = any(
                        inicio < turno.fecha_asistencia + turno.tratamiento.duracion_tratamiento
                        and turno.fecha_asistencia < fin
                        for turno in turnos_ocupados_dia
                    )
                    if not ocupado:
                        libres_dia += 1
                        if modo_agenda:
                            eventos.append({
                                "title": tratamiento.nombre_tratamiento or "Disponible",
                                "start": inicio.isoformat(),
                                "end": fin.isoformat(),
                                "backgroundColor": "#dcefe4",
                                "borderColor": "#77aa89",
                                "textColor": "#24583a",
                                "extendedProps": {
                                    "disponible": True,
                                    "categoria": categoria,
                                    "tratamientoId": tratamiento.pk,
                                    "tratamientoNombre": tratamiento.nombre_tratamiento,
                                },
                            })
                if categoria != Tratamiento.AgendaCategoria.CONSULTORIO:
                    libres_categoria += libres_dia
            if not modo_agenda:
                eventos.append({
                    "title": f"{etiquetas[categoria]}: {libres_categoria}",
                    "start": fecha_actual.isoformat(),
                    "allDay": True,
                    "backgroundColor": "transparent",
                    "borderColor": "transparent",
                    "textColor": "#24583a",
                    "extendedProps": {
                        "disponible": False,
                        "resumenCategoria": True,
                        "categoria": categoria,
                        "cantidadDisponible": libres_categoria,
                    },
                })
        fecha_actual += timedelta(days=1)
    return JsonResponse(eventos, safe=False)


@login_required
def agenda_turno_estado(request, turno_id):
    if not _puede_gestionar_agenda(request.user):
        raise PermissionDenied
    if request.method == "POST" and not _actualizar_estado_turno(
        turno_id,
        request.POST.get("estado"),
    ):
        messages.error(request, "No se pudo actualizar el turno en su estado actual.")
    return redirect("agenda")


@login_required
def turno_estado_paciente(request, dni, turno_id):
    if not _puede_gestionar_agenda(request.user):
        raise PermissionDenied
    paciente = get_object_or_404(Paciente, dni=dni)
    get_object_or_404(Turno, pk=turno_id, paciente=paciente)
    if request.method == "POST" and not _actualizar_estado_turno(
        turno_id,
        request.POST.get("estado"),
    ):
        messages.error(request, "No se pudo actualizar el turno en su estado actual.")
    return redirect(f"{reverse('paciente_detalle', kwargs={'dni': paciente.dni})}#turnos-panel")
