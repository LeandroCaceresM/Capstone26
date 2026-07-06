import uuid
import os


from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.db import models, transaction
from django.http import FileResponse
from django.conf import settings

from app.constants import ESTADO_APROBADO, ESTADO_EN_PROCESO, ESTADO_RECHAZADO, ROL_ADMIN, ROL_USUARIO, VIGENCIA_ACTIVA, VIGENCIA_INACTIVA
from app.models import *
from app.services.vecino_service import obtener_residencia_actual
from app.services.evento_service import obtener_eventos_junta
from app.utils import *
from app.decorators import role_required

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

# =========================
# VISTAS PRESIDENTE
# =========================

@never_cache
@role_required(ROL_ADMIN)
def panel_presidente_view(request):
    presidente = get_object_or_404(
        Vecino,
        id_vecino=request.session.get("vecino_id")
    )

    residencia = obtener_residencia_actual(presidente)

    junta = None
    solicitudes_pendientes = 0
    certificados_emitidos = 0
    noticias_activas = 0
    eventos_proximos = 0
    cantidad_vecinos = 0
    ultimas_solicitudes = []

    if residencia:
        junta = residencia.id_vivienda.id_junta

        vecinos_ids = HistVivienda.objects.filter(
            id_vivienda__id_junta=junta,
            fecha_ter__isnull=True
        ).values_list("id_vecino", flat=True)

        solicitudes_pendientes = Solicitud.objects.filter(
            id_vecino__in=vecinos_ids,
            estado=ESTADO_EN_PROCESO
        ).count()

        certificados_emitidos = CertificadoDeResidencia.objects.filter(
            id_vecino2=presidente
        ).count()

        noticias_activas = Noticia.objects.filter(
            id_junta=junta,
            vigencia=VIGENCIA_ACTIVA
        ).count()

        eventos_proximos = Evento.objects.filter(
            id_junta=junta,
            vigencia=VIGENCIA_ACTIVA,
            fecha_evento__gte=timezone.now()
        ).count()

        ultimas_solicitudes = Solicitud.objects.filter(
            id_vecino__in=vecinos_ids
        ).select_related(
            "id_vecino",
            "id_tsolicitud"
        ).order_by("-fecha_solicitud")[:5]
        
        cantidad_vecinos = HistVivienda.objects.filter(
            id_vivienda__id_junta=junta,
            fecha_ter__isnull=True
        ).count()

    return render(request, "panel_presidente.html", {
        "presidente": presidente,
        "junta": junta,
        "solicitudes_pendientes": solicitudes_pendientes,
        "certificados_emitidos": certificados_emitidos,
        "noticias_activas": noticias_activas,
        "eventos_proximos": eventos_proximos,
        "ultimas_solicitudes": ultimas_solicitudes,
        "cantidad_vecinos": cantidad_vecinos,
    })
    
    
# =========================
# VISTAS VIVIENDAS
# =========================

@never_cache
@role_required(ROL_ADMIN)
def viviendas_junta_view(request):
    presidente = get_object_or_404(
        Vecino,
        id_vecino=request.session.get("vecino_id")
    )

    residencia = obtener_residencia_actual(presidente)

    if not residencia:
        messages.error(request, "No perteneces a ninguna junta.")
        return redirect("panel_presidente")

    junta = residencia.id_vivienda.id_junta

    viviendas = Vivienda.objects.filter(
        id_junta=junta,
    ).order_by("nombre_calle", "numero_calle")

    viviendas_data = []

    for vivienda in viviendas:
        residentes_activos = HistVivienda.objects.filter(
            id_vivienda=vivienda,
            fecha_ter__isnull=True
        ).select_related("id_vecino")

        viviendas_data.append({
            "vivienda": vivienda,
            "residentes": residentes_activos,
            "ocupada": residentes_activos.exists()
        })
        
    total_viviendas = len(viviendas_data)
    viviendas_ocupadas = sum(1 for item in viviendas_data if item["ocupada"])
    viviendas_disponibles = total_viviendas - viviendas_ocupadas
        

    return render(request, "presidente/viviendas_junta.html", {
        "junta": junta,
        "viviendas_data": viviendas_data,
        "total_viviendas": total_viviendas,
        "viviendas_ocupadas": viviendas_ocupadas,
        "viviendas_disponibles": viviendas_disponibles,
    })

@never_cache
@role_required(ROL_ADMIN)
def crear_vivienda_view(request):
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
        tipo_vivienda = request.POST.get("tipo_vivienda")
        nombre_calle = limpiar_mayusculas(request.POST.get("nombre_calle"))
        numero_calle = request.POST.get("numero_calle")
        num_block = request.POST.get("num_block") or None
        num_dpto = request.POST.get("num_dpto") or None
        observacion = limpiar_texto(request.POST.get("observacion"))

        if tipo_vivienda == "C":
            num_block = None
            num_dpto = None

        if Vivienda.objects.filter(
            id_junta=junta,
            nombre_calle=nombre_calle,
            numero_calle=numero_calle,
            num_block=num_block,
            num_dpto=num_dpto
        ).exists():
            messages.error(request, "Esta vivienda ya existe en la junta.")
            return redirect("crear_vivienda")

        Vivienda.objects.create(
            id_vivienda=uuid.uuid4(),
            tipo_vivienda=tipo_vivienda,
            nombre_calle=nombre_calle,
            numero_calle=numero_calle,
            num_block=num_block,
            num_dpto=num_dpto,
            id_junta=junta,
            observacion=observacion,
        )

        messages.success(request, "Vivienda creada correctamente.")
        return redirect("viviendas_junta")

    return render(request, "presidente/crear_vivienda.html", {
        "junta": junta
    })


@never_cache
@role_required(ROL_ADMIN)
def eliminar_vivienda_view(request, id_vivienda):
    presidente = get_object_or_404(
        Vecino,
        id_vecino=request.session.get("vecino_id")
    )

    residencia = obtener_residencia_actual(presidente)

    if not residencia:
        messages.error(request, "No perteneces a ninguna junta.")
        return redirect("panel_presidente")

    junta = residencia.id_vivienda.id_junta

    vivienda = get_object_or_404(
        Vivienda,
        id_vivienda=id_vivienda,
        id_junta=junta
    )

    tiene_historial = HistVivienda.objects.filter(
        id_vivienda=vivienda
    ).exists()

    if request.method == "POST":
        if tiene_historial:
            messages.error(
                request,
                "No se puede eliminar esta vivienda porque tiene historial de residentes."
            )
            return redirect("detalle_vivienda", id_vivienda=vivienda.id_vivienda)

        vivienda.delete()

        messages.success(request, "Vivienda eliminada correctamente.")
        return redirect("viviendas_junta")

    return render(request, "presidente/eliminar_vivienda.html", {
        "vivienda": vivienda,
        "tiene_historial": tiene_historial,
    })

@never_cache
@role_required(ROL_ADMIN)
def detalle_vivienda_view(request, id_vivienda):
    presidente = get_object_or_404(
        Vecino,
        id_vecino=request.session.get("vecino_id")
    )

    residencia = obtener_residencia_actual(presidente)

    if not residencia:
        messages.error(request, "No perteneces a ninguna junta.")
        return redirect("panel_presidente")

    junta = residencia.id_vivienda.id_junta

    vivienda = get_object_or_404(
        Vivienda,
        id_vivienda=id_vivienda,
        id_junta=junta
    )

    residentes_actuales = HistVivienda.objects.filter(
        id_vivienda=vivienda,
        fecha_ter__isnull=True
    ).select_related("id_vecino")

    historial_residentes = HistVivienda.objects.filter(
        id_vivienda=vivienda
    ).select_related("id_vecino").order_by("-fecha_ini")

    return render(request, "presidente/detalle_vivienda.html", {
        "junta": junta,
        "vivienda": vivienda,
        "residentes_actuales": residentes_actuales,
        "historial_residentes": historial_residentes,
    })


@never_cache
@role_required(ROL_ADMIN)
def editar_vivienda_view(request, id_vivienda):
    presidente = get_object_or_404(Vecino, id_vecino=request.session.get("vecino_id"))
    residencia = obtener_residencia_actual(presidente)

    if not residencia:
        messages.error(request, "No perteneces a ninguna junta.")
        return redirect("panel_presidente")

    junta = residencia.id_vivienda.id_junta

    vivienda = get_object_or_404(
        Vivienda,
        id_vivienda=id_vivienda,
        id_junta=junta,
    )

    if request.method == "POST":
        tipo_vivienda = request.POST.get("tipo_vivienda")
        nombre_calle = limpiar_mayusculas(request.POST.get("nombre_calle"))
        numero_calle = request.POST.get("numero_calle")
        num_block = request.POST.get("num_block") or None
        num_dpto = request.POST.get("num_dpto") or None
        observacion = limpiar_texto(request.POST.get("observacion"))

        if tipo_vivienda == "C":
            num_block = None
            num_dpto = None

        existe = Vivienda.objects.filter(
            id_junta=junta,
            nombre_calle=nombre_calle,
            numero_calle=numero_calle,
            num_block=num_block,
            num_dpto=num_dpto,
        ).exclude(id_vivienda=vivienda.id_vivienda).exists()

        if existe:
            messages.error(request, "Ya existe otra vivienda con esa dirección.")
            return redirect("editar_vivienda", id_vivienda=vivienda.id_vivienda)

        vivienda.tipo_vivienda = tipo_vivienda
        vivienda.nombre_calle = nombre_calle
        vivienda.numero_calle = numero_calle
        vivienda.num_block = num_block
        vivienda.num_dpto = num_dpto
        vivienda.observacion = observacion
        vivienda.save()

        messages.success(request, "Vivienda actualizada correctamente.")
        return redirect("detalle_vivienda", id_vivienda=vivienda.id_vivienda)

    return render(request, "presidente/editar_vivienda.html", {
        "vivienda": vivienda,
        "junta": junta
    })

    presidente = get_object_or_404(Vecino, id_vecino=request.session.get("vecino_id"))
    residencia = obtener_residencia_actual(presidente)

    if not residencia:
        messages.error(request, "No perteneces a ninguna junta.")
        return redirect("panel_presidente")

    junta = residencia.id_vivienda.id_junta

    vivienda = get_object_or_404(
        Vivienda,
        id_vivienda=id_vivienda,
        id_junta=junta,
        vigencia=VIGENCIA_ACTIVA
    )

    tiene_residentes = HistVivienda.objects.filter(
        id_vivienda=vivienda,
        fecha_ter__isnull=True
    ).exists()

    if request.method == "POST":
        if tiene_residentes:
            messages.error(request, "No puedes desactivar una vivienda con residentes activos.")
            return redirect("detalle_vivienda", id_vivienda=vivienda.id_vivienda)

        vivienda.vigencia = VIGENCIA_INACTIVA
        vivienda.save()

        messages.success(request, "Vivienda desactivada correctamente.")
        return redirect("viviendas_junta")

    return render(request, "presidente/desactivar_vivienda.html", {
        "vivienda": vivienda,
        "tiene_residentes": tiene_residentes
    })


@never_cache
@role_required(ROL_ADMIN)
def asignar_vecino_vivienda_view(request, id_vivienda):
    presidente = get_object_or_404(
        Vecino,
        id_vecino=request.session.get("vecino_id")
    )

    residencia = obtener_residencia_actual(presidente)

    if not residencia:
        messages.error(request, "No perteneces a ninguna junta.")
        return redirect("panel_presidente")

    junta = residencia.id_vivienda.id_junta

    vivienda = get_object_or_404(
        Vivienda,
        id_vivienda=id_vivienda,
        id_junta=junta
    )

    vecinos_con_vivienda = HistVivienda.objects.filter(
        fecha_ter__isnull=True
    ).values_list("id_vecino", flat=True)

    vecinos_disponibles = Vecino.objects.filter(
        vigencia=VIGENCIA_ACTIVA,
        id_rol__nombre_rol=ROL_USUARIO
    ).exclude(
        id_vecino__in=vecinos_con_vivienda
    ).order_by(
        "apell_paterno",
        "pri_nombre"
    )

    if request.method == "POST":

        vecino = get_object_or_404(
            Vecino,
            id_vecino=request.POST.get("id_vecino")
        )

        ya_tiene_vivienda = HistVivienda.objects.filter(
            id_vecino=vecino,
            fecha_ter__isnull=True
        ).exists()

        if ya_tiene_vivienda:
            messages.error(
                request,
                "Este vecino ya tiene una vivienda activa."
            )
            return redirect(
                "asignar_vecino_vivienda",
                id_vivienda=vivienda.id_vivienda
            )

        HistVivienda.objects.create(
            id_hist_vivienda=uuid.uuid4(),
            fecha_ini=timezone.now().date(),
            fecha_ter=None,
            id_vivienda=vivienda,
            id_vecino=vecino
        )

        messages.success(
            request,
            "Vecino asignado correctamente."
        )

        return redirect(
            "detalle_vivienda",
            id_vivienda=vivienda.id_vivienda
        )

    return render(request, "presidente/asignar_vecino_vivienda.html", {
        "junta": junta,
        "vivienda": vivienda,
        "vecinos_disponibles": vecinos_disponibles,
    })


@never_cache
@role_required(ROL_ADMIN)
def retirar_vecino_vivienda_view(request, id_vivienda, id_vecino):
    presidente = get_object_or_404(
        Vecino,
        id_vecino=request.session.get("vecino_id")
    )

    residencia = obtener_residencia_actual(presidente)

    if not residencia:
        messages.error(request, "No perteneces a ninguna junta.")
        return redirect("panel_presidente")

    junta = residencia.id_vivienda.id_junta

    vivienda = get_object_or_404(
        Vivienda,
        id_vivienda=id_vivienda,
        id_junta=junta
    )

    vecino = get_object_or_404(
        Vecino,
        id_vecino=id_vecino
    )

    registro = get_object_or_404(
        HistVivienda,
        id_vivienda=vivienda,
        id_vecino=vecino,
        fecha_ter__isnull=True
    )

    if request.method == "POST":
        registro.fecha_ter = timezone.now().date()
        registro.save()

        messages.success(request, "Vecino retirado correctamente de la vivienda.")
        return redirect("detalle_vivienda", id_vivienda=vivienda.id_vivienda)

    return render(request, "presidente/retirar_vecino_vivienda.html", {
        "vivienda": vivienda,
        "vecino": vecino,
    })



# =========================
# VISTAS SOLICITUDES
# =========================

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

    solicitudes_vecinos_junta = Solicitud.objects.filter(
        id_vecino__in=vecinos_ids
    )

    solicitudes_incorporacion_ids = SolicitudIncorporacion.objects.filter(
        id_junta=junta
    ).values_list("id_solicitud", flat=True)

    solicitudes_incorporacion = Solicitud.objects.filter(
        id_solicitud__in=solicitudes_incorporacion_ids
    )

    solicitudes = (
        solicitudes_vecinos_junta | solicitudes_incorporacion
    ).distinct().select_related(
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
        comentario_presidente = limpiar_texto(request.POST.get("comentario_presidente"))

        if accion == "aprobar":
            nuevo_estado = ESTADO_APROBADO
        elif accion == "rechazar":
            nuevo_estado = ESTADO_RECHAZADO
        else:
            messages.error(request, "Acción no válida.")
            return redirect("solicitudes_presidente")

        try:
            with transaction.atomic():

                if nuevo_estado == ESTADO_APROBADO and solicitud.id_tsolicitud.tipo_solicitud == "Cambio de domicilio":
                    cambio = get_object_or_404(
                        SolicitudCambioDomicilio,
                        id_solicitud=solicitud
                    )

                    vecino = solicitud.id_vecino
                    vivienda_destino = cambio.id_vivienda_destino

                    residencia_actual = HistVivienda.objects.filter(
                        id_vecino=vecino,
                        fecha_ter__isnull=True
                    ).first()

                    if residencia_actual:
                        residencia_actual.fecha_ter = timezone.now().date()
                        residencia_actual.save()

                    HistVivienda.objects.create(
                        id_hist_vivienda=uuid.uuid4(),
                        fecha_ini=timezone.now().date(),
                        fecha_ter=None,
                        id_vivienda=vivienda_destino,
                        id_vecino=vecino
                    )

                if nuevo_estado == ESTADO_APROBADO and solicitud.id_tsolicitud.tipo_solicitud == "Incorporación a junta":
                    incorporacion = get_object_or_404(
                        SolicitudIncorporacion,
                        id_solicitud=solicitud
                    )

                    vecino = solicitud.id_vecino
                    vivienda = incorporacion.id_vivienda

                    ya_tiene_residencia = HistVivienda.objects.filter(
                        id_vecino=vecino,
                        fecha_ter__isnull=True
                    ).exists()

                    if ya_tiene_residencia:
                        messages.error(request, "El vecino ya posee una residencia activa.")
                        return redirect("cerrar_solicitud", id_solicitud=solicitud.id_solicitud)

                    HistVivienda.objects.create(
                        id_hist_vivienda=uuid.uuid4(),
                        fecha_ini=timezone.now().date(),
                        fecha_ter=None,
                        id_vivienda=vivienda,
                        id_vecino=vecino
                    )

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

        except Exception as e:
            messages.error(request, f"Error al cerrar solicitud: {e}")
            return redirect("cerrar_solicitud", id_solicitud=solicitud.id_solicitud)

    cambio_domicilio = None
    residencia_actual = None
    incorporacion = None

    if solicitud.id_tsolicitud.tipo_solicitud == "Cambio de domicilio":
        cambio_domicilio = SolicitudCambioDomicilio.objects.filter(
            id_solicitud=solicitud
        ).select_related("id_vivienda_destino").first()

        residencia_actual = HistVivienda.objects.filter(
            id_vecino=solicitud.id_vecino,
            fecha_ter__isnull=True
        ).select_related("id_vivienda").first()

    if solicitud.id_tsolicitud.tipo_solicitud == "Incorporación a junta":
        incorporacion = SolicitudIncorporacion.objects.filter(
            id_solicitud=solicitud
        ).select_related(
            "id_junta",
            "id_junta__id_sector__id_comuna__id_region",
            "id_vivienda"
        ).first()

    return render(request, "presidente/cerrar_solicitud.html", {
        "solicitud": solicitud,
        "cambio_domicilio": cambio_domicilio,
        "residencia_actual": residencia_actual,
        "incorporacion": incorporacion,
    })


# =========================
# VISTAS CERTIFICADOS
# =========================

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
    

# =========================
# VISTAS NOTICIAS
# =========================

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

# =========================
# VISTAS EVENTOS
# =========================

@never_cache
@role_required(ROL_ADMIN)
def gestionar_eventos_view(request):
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
        Evento.objects.create(
            id_evento=uuid.uuid4(),
            titulo=limpiar_titulo(request.POST.get("titulo")),
            descripcion=limpiar_texto(request.POST.get("descripcion")),
            fecha_evento=request.POST.get("fecha_evento"),
            lugar=limpiar_titulo(request.POST.get("lugar")),
            vigencia=VIGENCIA_ACTIVA,
            id_junta=junta,
            id_vecino=presidente
        )

        messages.success(request, "Evento creado correctamente.")
        return redirect("gestionar_eventos")

    eventos = obtener_eventos_junta(junta)

    return render(request, "presidente/gestionar_eventos.html", {
        "junta": junta,
        "eventos": eventos,
    })


@never_cache
@role_required(ROL_ADMIN)
def editar_evento_view(request, id_evento):
    presidente = get_object_or_404(
        Vecino,
        id_vecino=request.session.get("vecino_id")
    )

    residencia = obtener_residencia_actual(presidente)

    if not residencia:
        messages.error(request, "No perteneces a ninguna junta.")
        return redirect("panel_presidente")

    junta = residencia.id_vivienda.id_junta

    evento = get_object_or_404(
        Evento,
        id_evento=id_evento,
        id_junta=junta,
        vigencia=VIGENCIA_ACTIVA
    )

    if request.method == "POST":
        evento.titulo = limpiar_titulo(request.POST.get("titulo"))
        evento.descripcion = limpiar_texto(request.POST.get("descripcion"))
        evento.fecha_evento = request.POST.get("fecha_evento")
        evento.lugar = limpiar_titulo(request.POST.get("lugar"))
        evento.save()

        messages.success(request, "Evento actualizado correctamente.")
        return redirect("gestionar_eventos")

    return render(request, "presidente/editar_evento.html", {
        "evento": evento
    })


@never_cache
@role_required(ROL_ADMIN)
def eliminar_evento_view(request, id_evento):
    presidente = get_object_or_404(
        Vecino,
        id_vecino=request.session.get("vecino_id")
    )

    residencia = obtener_residencia_actual(presidente)

    if not residencia:
        messages.error(request, "No perteneces a ninguna junta.")
        return redirect("panel_presidente")

    junta = residencia.id_vivienda.id_junta

    evento = get_object_or_404(
        Evento,
        id_evento=id_evento,
        id_junta=junta,
        vigencia=VIGENCIA_ACTIVA
    )

    if request.method == "POST":
        evento.vigencia = VIGENCIA_INACTIVA
        evento.save()

        messages.success(request, "Evento eliminado correctamente.")
        return redirect("gestionar_eventos")

    return render(request, "presidente/eliminar_evento.html", {
        "evento": evento
    })

# =========================
# VISTAS REPORTES  
# =========================

@never_cache
@role_required(ROL_ADMIN)
def reporte_junta_view(request):
    presidente = get_object_or_404(
        Vecino,
        id_vecino=request.session.get("vecino_id")
    )

    residencia = obtener_residencia_actual(presidente)

    if not residencia:
        messages.error(request, "No perteneces a ninguna junta.")
        return redirect("panel_presidente")

    junta = residencia.id_vivienda.id_junta

    viviendas = Vivienda.objects.filter(id_junta=junta)

    vecinos_ids = HistVivienda.objects.filter(
        id_vivienda__id_junta=junta,
        fecha_ter__isnull=True
    ).values_list("id_vecino", flat=True).distinct()

    total_viviendas = viviendas.count()
    viviendas_con_residentes = viviendas.filter(
        histvivienda__fecha_ter__isnull=True
    ).distinct().count()

    viviendas_sin_residentes = total_viviendas - viviendas_con_residentes
    total_vecinos = vecinos_ids.count()

    solicitudes = Solicitud.objects.filter(
        id_vecino__in=vecinos_ids
    )

    solicitudes_pendientes = solicitudes.filter(
        estado=ESTADO_EN_PROCESO
    ).count()

    solicitudes_aprobadas = solicitudes.filter(
        estado=ESTADO_APROBADO
    ).count()

    solicitudes_rechazadas = solicitudes.filter(
        estado=ESTADO_RECHAZADO
    ).count()

    certificados_emitidos = CertificadoDeResidencia.objects.filter(
        id_vecino__in=vecinos_ids
    ).count()

    return render(request, "presidente/reporte_junta.html", {
        "junta": junta,
        "presidente": presidente,
        "total_viviendas": total_viviendas,
        "viviendas_con_residentes": viviendas_con_residentes,
        "viviendas_sin_residentes": viviendas_sin_residentes,
        "total_vecinos": total_vecinos,
        "solicitudes_pendientes": solicitudes_pendientes,
        "solicitudes_aprobadas": solicitudes_aprobadas,
        "solicitudes_rechazadas": solicitudes_rechazadas,
        "certificados_emitidos": certificados_emitidos,
    })


@never_cache
@role_required(ROL_ADMIN)
def reporte_junta_pdf_view(request):
    presidente = get_object_or_404(
        Vecino,
        id_vecino=request.session.get("vecino_id")
    )

    residencia = obtener_residencia_actual(presidente)

    if not residencia:
        messages.error(request, "No perteneces a ninguna junta.")
        return redirect("panel_presidente")

    junta = residencia.id_vivienda.id_junta
    viviendas = Vivienda.objects.filter(id_junta=junta)

    vecinos_ids = HistVivienda.objects.filter(
        id_vivienda__id_junta=junta,
        fecha_ter__isnull=True
    ).values_list("id_vecino", flat=True).distinct()

    total_viviendas = viviendas.count()
    viviendas_con_residentes = viviendas.filter(
        histvivienda__fecha_ter__isnull=True
    ).distinct().count()
    viviendas_sin_residentes = total_viviendas - viviendas_con_residentes
    total_vecinos = vecinos_ids.count()

    solicitudes = Solicitud.objects.filter(id_vecino__in=vecinos_ids)

    datos = {
        "Vecinos activos": total_vecinos,
        "Viviendas registradas": total_viviendas,
        "Viviendas con residentes": viviendas_con_residentes,
        "Viviendas sin residentes": viviendas_sin_residentes,
        "Solicitudes pendientes": solicitudes.filter(estado=ESTADO_EN_PROCESO).count(),
        "Solicitudes aprobadas": solicitudes.filter(estado=ESTADO_APROBADO).count(),
        "Solicitudes rechazadas": solicitudes.filter(estado=ESTADO_RECHAZADO).count(),
        "Certificados emitidos": CertificadoDeResidencia.objects.filter(
            id_vecino__in=vecinos_ids
        ).count(),
    }

    carpeta = os.path.join(settings.MEDIA_ROOT, "reportes")
    os.makedirs(carpeta, exist_ok=True)

    ruta_pdf = os.path.join(carpeta, f"reporte_{junta.id_junta}.pdf")

    c = canvas.Canvas(ruta_pdf, pagesize=letter)
    width, height = letter

    y = height - 60

    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(width / 2, y, "REPORTE GENERAL DE LA JUNTA")

    y -= 40
    c.setFont("Helvetica", 11)
    c.drawString(70, y, f"Junta: {junta.nombre}")

    y -= 20
    c.drawString(70, y, f"Presidente: {presidente.pri_nombre} {presidente.apell_paterno}")

    y -= 20
    c.drawString(70, y, f"Fecha emisión: {timezone.localtime(timezone.now()).strftime('%d/%m/%Y %H:%M')}")

    y -= 40
    c.setFont("Helvetica-Bold", 13)
    c.drawString(70, y, "Indicadores")

    y -= 25
    c.setFont("Helvetica", 11)

    for nombre, valor in datos.items():
        c.drawString(90, y, f"{nombre}: {valor}")
        y -= 22

    c.setFont("Helvetica", 9)
    c.drawCentredString(width / 2, 50, "Reporte emitido digitalmente a través de UrbanLink.")

    c.save()

    return FileResponse(
        open(ruta_pdf, "rb"),
        as_attachment=True,
        filename=f"reporte_general_{junta.nombre}.pdf"
    )