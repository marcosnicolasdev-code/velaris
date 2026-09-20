from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.utils import timezone
import unicodedata
import re

from .models import Paciente, Evolucion, Turno
from .forms import PacienteForm, TurnoForm
from usuarios.models import Profesional

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
    grupos_clinicos = {"Médico", "Enfermero", "Instrumentador"}
    puede_crear_medica = (
        hasattr(request.user, "profesional")
        or request.user.groups.filter(name__in=grupos_clinicos).exists()
    )
    puede_crear_privada = (
        not puede_crear_medica
        and (
            request.user.is_superuser
            or request.user.groups.filter(name="Recepcionista").exists()
        )
    )

    return render(
        request,
        "pacientes/paciente_detalle.html",
        {
            "paciente": paciente,
            "historia": historia,
            "evoluciones": evoluciones,
            "puede_crear_privada": puede_crear_privada,
            "puede_crear_medica": puede_crear_medica,
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
    profesional = getattr(request.user, "profesional", None)
    if profesional is None and not es_clinico:
        raise PermissionDenied

    paciente = get_object_or_404(Paciente, dni=dni)
    historia = paciente.get_historia_clinica()

    if request.method == "POST":
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
            descripcion = (
                f"Pte.:\n{motivo}\n\n"
                f"Antecedentes:\n{antecedentes}\n\n"
                f"Examen físico:\n{examen_fisico}\n\n"
                f"Se le indica:\n{se_indica}"
            )

        Evolucion.objects.create(
            historia_clinica=historia,
            profesional=profesional,
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
        {"paciente": paciente},
    )

#CRUD TURNOS

#CREATE
@login_required
def turno_crear(request, dni):
    paciente = get_object_or_404(Paciente, dni=dni)
    if request.method == "POST":
        form = TurnoForm(request.POST)
        if form.is_valid():
            turno = form.save(commit=False)
            turno.paciente = paciente
            turno.save()
            return redirect("paciente_detalle", dni=paciente.dni)
    else:
        form = TurnoForm()
    return render(request, "pacientes/turno_form.html", {"paciente": paciente, "form": form})


#READ
@login_required
def turno_lista(request, dni):
    paciente = get_object_or_404(Paciente, dni=dni)
    turnos = Turno.objects.filter(paciente=paciente)
    return render(request, "pacientes/turno_lista.html", {"paciente": paciente, "turnos": turnos})

#UPDATE
@login_required
def turno_editar(request, dni, turno_id):
    paciente = get_object_or_404(Paciente, dni=dni)
    turno = get_object_or_404(Turno, id=turno_id, paciente=paciente)
    if request.method == "POST":
        form = TurnoForm(request.POST, instance=turno)
        if form.is_valid():
            form.save()
            return redirect("paciente_detalle", dni=paciente.dni)
    else:
        form = TurnoForm(instance=turno)
    return render(request, "pacientes/turno_form.html", {"paciente": paciente, "form": form})

#DELETE
@login_required
def turno_borrar(request, dni, turno_id):
    paciente = get_object_or_404(Paciente, dni=dni)
    turno = get_object_or_404(Turno, id=turno_id, paciente=paciente)
    if request.method == "POST":
        turno.delete()
        return redirect("paciente_detalle", dni=paciente.dni)
    return render(request, "pacientes/turno_confirmar_eliminacion.html", {"paciente": paciente, "turno": turno})

#CRUD AGENDA

@login_required
def agenda(request):
    return render(request, "pacientes/agenda.html")

