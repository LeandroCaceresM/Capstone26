import uuid

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.db import models

from app.constants import ESTADO_APROBADO, ESTADO_EN_PROCESO, ESTADO_RECHAZADO, ROL_ADMIN, VIGENCIA_ACTIVA, VIGENCIA_INACTIVA
from app.models import *
from app.services.vecino_service import obtener_residencia_actual
from app.utils import *
from app.decorators import role_required

# =========================
# VISTAS PRESIDENTE
# =========================

@never_cache
@role_required(ROL_ADMIN)
def panel_presidente_view(request):
    return render(request, "panel_presidente.html")


@never_cache
@role_required(ROL_ADMIN)
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
    filtro_tipo = request.GET.get("tipo", "Todas")
    orden = request.GET.get("orden", "recientes")
    busqueda = request.GET.get("q", "")

    tipos = Tiposolicitud.objects.all().order_by("tipo_solicitud")

    vecinos_ids = HistVivienda.objects.filter(
        id_vivienda__id_junta=junta,
        fecha_ter__isnull=True
    ).values_list("id_vecino", flat=True)

    solicitudes = Solicitud.objects.filter(
        id_vecino__in=vecinos_ids
    ).select_related(
        "id_vecino",
        "id_tsolicitud"
    )

    if filtro_estado != "Todas":
        solicitudes = solicitudes.filter(estado=filtro_estado)

    if filtro_tipo != "Todas":
        solicitudes = solicitudes.filter(
            id_tsolicitud__id_tsolicitud=filtro_tipo
        )

    if busqueda:
        solicitudes = solicitudes.filter(
            models.Q(id_vecino__pri_nombre__icontains=busqueda) |
            models.Q(id_vecino__seg_nombre__icontains=busqueda) |
            models.Q(id_vecino__apell_paterno__icontains=busqueda) |
            models.Q(id_vecino__apell_materno__icontains=busqueda) |
            models.Q(id_vecino__rut__icontains=busqueda)
        )

    if orden == "antiguas":
        solicitudes = solicitudes.order_by("fecha_solicitud")
    elif orden == "vecino_az":
        solicitudes = solicitudes.order_by(
            "id_vecino__pri_nombre",
            "id_vecino__apell_paterno"
        )
    elif orden == "vecino_za":
        solicitudes = solicitudes.order_by(
            "-id_vecino__pri_nombre",
            "-id_vecino__apell_paterno"
        )
    elif orden == "estado":
        solicitudes = solicitudes.order_by("estado", "-fecha_solicitud")
    elif orden == "tipo":
        solicitudes = solicitudes.order_by(
            "id_tsolicitud__tipo_solicitud",
            "-fecha_solicitud"
        )
    else:
        solicitudes = solicitudes.order_by("-fecha_solicitud")

    solicitudes_data = []

    for solicitud in solicitudes:
        hist_cierre = HistEstSol.objects.filter(
            id_solicitud=solicitud,
            id_est__nomb_est_sol__in=[ESTADO_APROBADO, ESTADO_RECHAZADO]
        ).order_by("-fecha_cb_estado").first()

        solicitudes_data.append({
            "solicitud": solicitud,
            "fecha_resuelta": hist_cierre.fecha_cb_estado if hist_cierre else None
        })

    return render(request, "presidente/solicitudes.html", {
        "junta": junta,
        "solicitudes_data": solicitudes_data,
        "filtro_estado": filtro_estado,
        "filtro_tipo": filtro_tipo,
        "orden": orden,
        "busqueda": busqueda,
        "tipos": tipos,
    })
    

@never_cache
@role_required(ROL_ADMIN)
def cerrar_solicitud_view(request, id_solicitud):
    solicitud = get_object_or_404(Solicitud, id_solicitud=id_solicitud)

    if solicitud.estado != ESTADO_EN_PROCESO:
        messages.error(request, "Esta solicitud ya fue cerrada.")
        return redirect("solicitudes_presidente")

    if request.method == "POST":
        accion = request.POST.get("accion")
        comentario_presidente = limpiar_texto(
            request.POST.get("comentario_presidente")
        )

        if accion == "aprobar":
            nuevo_estado = ESTADO_APROBADO
        elif accion == "rechazar":
            nuevo_estado = ESTADO_RECHAZADO
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
@role_required(ROL_ADMIN)
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
    
@never_cache
@role_required(ROL_ADMIN)
def crear_noticia_view(request):
    presidente = get_object_or_404(
        Vecino,
        id_vecino=request.session.get("vecino_id")
    )

    residencia = obtener_residencia_actual(presidente)

    if not residencia:
        messages.error(request, "No perteneces a ninguna junta.")
        return redirect("panel_presidente")

    junta = residencia.id_vivienda.id_junta

    if request.method == "POST":

        Noticia.objects.create(
            id_noticia=uuid.uuid4(),
            titulo=limpiar_titulo(request.POST.get("titulo")),
            descripcion=limpiar_texto(request.POST.get("descripcion")),
            fecha_publicacion=timezone.now(),
            vigencia=VIGENCIA_ACTIVA,
            id_junta=junta,
            id_vecino=presidente
        )

        messages.success(request, "Noticia publicada correctamente.")
        return redirect("crear_noticia")

    return render(request, "presidente/crear_noticia.html")


@never_cache
@role_required(ROL_ADMIN)
def editar_noticia_view(request, id_noticia):
    presidente = get_object_or_404(
        Vecino,
        id_vecino=request.session.get("vecino_id")
    )

    residencia = obtener_residencia_actual(presidente)

    if not residencia:
        messages.error(request, "No perteneces a ninguna junta.")
        return redirect("panel_presidente")

    junta = residencia.id_vivienda.id_junta

    noticia = get_object_or_404(
        Noticia,
        id_noticia=id_noticia,
        id_junta=junta,
        vigencia=VIGENCIA_ACTIVA
    )

    if request.method == "POST":
        noticia.titulo = limpiar_titulo(request.POST.get("titulo"))
        noticia.descripcion = limpiar_texto(request.POST.get("descripcion"))
        noticia.save()

        messages.success(request, "Noticia actualizada correctamente.")
        return redirect("gestionar_noticias")

    return render(request, "presidente/editar_noticia.html", {
        "noticia": noticia
    })


@never_cache
@role_required(ROL_ADMIN)
def eliminar_noticia_view(request, id_noticia):
    presidente = get_object_or_404(
        Vecino,
        id_vecino=request.session.get("vecino_id")
    )

    residencia = obtener_residencia_actual(presidente)

    if not residencia:
        messages.error(request, "No perteneces a ninguna junta.")
        return redirect("panel_presidente")

    junta = residencia.id_vivienda.id_junta

    noticia = get_object_or_404(
        Noticia,
        id_noticia=id_noticia,
        id_junta=junta,
        vigencia=VIGENCIA_ACTIVA
    )

    if request.method == "POST":
        noticia.vigencia = VIGENCIA_INACTIVA
        noticia.save()

        messages.success(request, "Noticia eliminada correctamente.")
        return redirect("gestionar_noticias")

    return render(request, "presidente/eliminar_noticia.html", {
        "noticia": noticia
    })



@never_cache
@role_required(ROL_ADMIN)
def gestionar_noticias_view(request):
    presidente = get_object_or_404(
        Vecino,
        id_vecino=request.session.get("vecino_id")
    )

    residencia = obtener_residencia_actual(presidente)

    if not residencia:
        messages.error(request, "No perteneces a ninguna junta.")
        return redirect("panel_presidente")

    junta = residencia.id_vivienda.id_junta

    if request.method == "POST":
        titulo = limpiar_titulo(request.POST.get("titulo"))
        descripcion = limpiar_texto(request.POST.get("descripcion"))

        Noticia.objects.create(
            id_noticia=uuid.uuid4(),
            titulo=titulo,
            descripcion=descripcion,
            fecha_publicacion=timezone.now(),
            vigencia=VIGENCIA_ACTIVA,
            id_junta=junta,
            id_vecino=presidente
        )

        messages.success(request, "Noticia publicada correctamente.")
        return redirect("gestionar_noticias")

    noticias = Noticia.objects.filter(
        id_junta=junta,
        vigencia=VIGENCIA_ACTIVA
    ).select_related("id_vecino").order_by("-fecha_publicacion")

    return render(request, "presidente/gestionar_noticias.html", {
        "junta": junta,
        "noticias": noticias,
    })

