from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.db import models

from app.models import *
from app.utils import *
from app.decorators import role_required

# =========================
# VISTAS PRESIDENTE
# =========================

@never_cache
@role_required("Admin")
def panel_presidente_view(request):
    return render(request, "panel_presidente.html")


@never_cache
@role_required("Admin")
def solicitudes_presidente_view(request):
    presidente = get_object_or_404(
        Vecino,
        id_vecino=request.session.get("vecino_id")
    )

    residencia_presidente = HistVivienda.objects.filter(
        id_vecino=presidente,
        fecha_ter__isnull=True
    ).select_related("id_vivienda__id_junta").first()

    if not residencia_presidente:
        messages.error(request, "No perteneces a ninguna junta.")
        return redirect("panel_presidente")

    junta = residencia_presidente.id_vivienda.id_junta

    filtro_estado = request.GET.get("estado", "Todas")
    busqueda = request.GET.get("q", "")

    vecinos_ids = HistVivienda.objects.filter(
        id_vivienda__id_junta=junta,
        fecha_ter__isnull=True
    ).values_list("id_vecino", flat=True)

    solicitudes = Solicitud.objects.filter(
        id_vecino__in=vecinos_ids
    ).select_related(
        "id_vecino",
        "id_tsolicitud"
    ).order_by("-fecha_solicitud")

    if filtro_estado != "Todas":
        solicitudes = solicitudes.filter(estado=filtro_estado)

    if busqueda:
        solicitudes = solicitudes.filter(
            models.Q(id_vecino__pri_nombre__icontains=busqueda) |
            models.Q(id_vecino__seg_nombre__icontains=busqueda) |
            models.Q(id_vecino__apell_paterno__icontains=busqueda) |
            models.Q(id_vecino__apell_materno__icontains=busqueda) |
            models.Q(id_vecino__rut__icontains=busqueda)
        )

    solicitudes_data = []

    for solicitud in solicitudes:
        hist_cierre = HistEstSol.objects.filter(
            id_solicitud=solicitud,
            id_est__nomb_est_sol__in=["APROBADO", "RECHAZADO"]
        ).order_by("-fecha_cb_estado").first()

        solicitudes_data.append({
            "solicitud": solicitud,
            "fecha_resuelta": hist_cierre.fecha_cb_estado if hist_cierre else None
        })

    return render(request, "presidente/solicitudes.html", {
        "junta": junta,
        "solicitudes_data": solicitudes_data,
        "filtro_estado": filtro_estado,
        "busqueda": busqueda,
    })


@never_cache
@role_required("Admin")
def cerrar_solicitud_view(request, id_solicitud):
    solicitud = get_object_or_404(Solicitud, id_solicitud=id_solicitud)

    if solicitud.estado != "EN PROCESO":
        messages.error(request, "Esta solicitud ya fue cerrada.")
        return redirect("solicitudes_presidente")

    if request.method == "POST":
        accion = request.POST.get("accion")
        comentario_presidente = limpiar_texto(
            request.POST.get("comentario_presidente")
        )

        if accion == "aprobar":
            nuevo_estado = "APROBADO"
        elif accion == "rechazar":
            nuevo_estado = "RECHAZADO"
        else:
            messages.error(request, "Acción no válida.")
            return redirect("solicitudes_presidente")

        solicitud.estado = nuevo_estado
        solicitud.comentario_presidente = comentario_presidente
        solicitud.save()

        estado_obj = EstadoSolicitud.objects.get(nomb_est_sol=nuevo_estado)

        HistEstSol.objects.create(
            id_solicitud=solicitud,
            id_est=estado_obj,
            fecha_cb_estado=timezone.now()
        )

        messages.success(request, "Solicitud cerrada correctamente.")
        return redirect("solicitudes_presidente")

    return render(request, "presidente/cerrar_solicitud.html", {
        "solicitud": solicitud
    })


@never_cache
@role_required("Admin")
def certificados_presidente_view(request):
    presidente = get_object_or_404(
        Vecino,
        id_vecino=request.session.get("vecino_id")
    )

    busqueda = request.GET.get("q", "")

    certificados = CertificadoDeResidencia.objects.filter(
        id_vecino2=presidente
    ).select_related("id_vecino").order_by("-fecha_emision")

    if busqueda:
        certificados = certificados.filter(
            models.Q(id_vecino__pri_nombre__icontains=busqueda) |
            models.Q(id_vecino__seg_nombre__icontains=busqueda) |
            models.Q(id_vecino__apell_paterno__icontains=busqueda) |
            models.Q(id_vecino__apell_materno__icontains=busqueda) |
            models.Q(id_vecino__rut__icontains=busqueda)
        )

    return render(request, "presidente/certificados.html", {
        "certificados": certificados,
        "busqueda": busqueda,
    })