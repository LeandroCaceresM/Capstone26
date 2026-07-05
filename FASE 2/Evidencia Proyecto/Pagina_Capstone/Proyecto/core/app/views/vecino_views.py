import os
import uuid

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from django.views.decorators.cache import never_cache

from app.constants import (
    ESTADO_EN_PROCESO,
    ESTADO_APROBADO,
    ESTADO_RECHAZADO,
    ROL_ADMIN,
    ROL_USUARIO,
)
from app.models import *
from app.supabase_storage_client import supabase_storage
from app.utils import *
from app.decorators import login_required_custom, role_required
from app.services.noticia_service import obtener_noticias_junta, obtener_ultimas_noticias_junta
from app.services.evento_service import obtener_proximos_eventos_junta

from app.services.vecino_service import (
    obtener_residencia_actual,
    obtener_cargo_actual,
)

from app.services.junta_service import (
    obtener_vecinos_activos_junta,
    construir_vecinos_data,
)

from app.services.solicitud_service import construir_solicitudes_data


@never_cache
@role_required(ROL_USUARIO)
def panel_vecino_view(request):
    vecino = get_object_or_404(Vecino, id_vecino=request.session.get("vecino_id"))

    residencia = obtener_residencia_actual(vecino)
    cargo_actual = obtener_cargo_actual(vecino)
        
    ultimas_noticias = []
    proximos_eventos = []

    if residencia:
        junta = residencia.id_vivienda.id_junta
        ultimas_noticias = obtener_ultimas_noticias_junta(junta, limite=3)
        proximos_eventos = obtener_proximos_eventos_junta(junta, limite=3)    

    solicitudes_en_proceso = Solicitud.objects.filter(
        id_vecino=vecino,
        estado=ESTADO_EN_PROCESO
    ).count()

    solicitudes_aprobadas = Solicitud.objects.filter(
        id_vecino=vecino,
        estado=ESTADO_APROBADO
    ).count()

    solicitudes_rechazadas = Solicitud.objects.filter(
        id_vecino=vecino,
        estado=ESTADO_RECHAZADO
    ).count()

    certificados_emitidos = CertificadoDeResidencia.objects.filter(
        id_vecino=vecino
    ).count()

    ultimas_solicitudes = Solicitud.objects.filter(
        id_vecino=vecino
    ).select_related("id_tsolicitud").order_by("-fecha_solicitud")[:3]

    return render(request, "panel_vecino.html", {
        "vecino": vecino,
        "residencia": residencia,
        "cargo_actual": cargo_actual,
        "solicitudes_en_proceso": solicitudes_en_proceso,
        "solicitudes_aprobadas": solicitudes_aprobadas,
        "solicitudes_rechazadas": solicitudes_rechazadas,
        "certificados_emitidos": certificados_emitidos,
        "ultimas_solicitudes": ultimas_solicitudes,
        "ultimas_noticias": ultimas_noticias,
        "proximos_eventos": proximos_eventos,
    })


@never_cache
@role_required(ROL_USUARIO)
def solicitar_incorporacion_view(request):
    vecino = get_object_or_404(
        Vecino,
        id_vecino=request.session.get("vecino_id")
    )

    residencia_actual = obtener_residencia_actual(vecino)

    if residencia_actual:
        messages.error(request, "Ya perteneces a una junta de vecinos.")
        return redirect("panel_vecino")

    solicitud_pendiente = Solicitud.objects.filter(
        id_vecino=vecino,
        id_tsolicitud__tipo_solicitud="Incorporación a junta",
        estado=ESTADO_EN_PROCESO
    ).exists()

    if solicitud_pendiente:
        messages.error(request, "Ya tienes una solicitud de incorporación en proceso.")
        return redirect("mis_solicitudes")

    regiones = Region.objects.all().order_by("nom_region")

    comunas = Comuna.objects.select_related(
        "id_region"
    ).order_by("nom_comuna")

    juntas = Juntavecinos.objects.select_related(
        "id_sector__id_comuna__id_region"
    ).order_by("nombre")

    viviendas = Vivienda.objects.select_related(
        "id_junta"
    ).order_by(
        "id_junta__nombre",
        "nombre_calle",
        "numero_calle"
    )

    if request.method == "POST":
        junta = get_object_or_404(
            Juntavecinos,
            id_junta=request.POST.get("id_junta")
        )

        vivienda = get_object_or_404(
            Vivienda,
            id_vivienda=request.POST.get("id_vivienda"),
            id_junta=junta
        )

        tipo_documento = "Evidencia de domicilio"
        documento = request.FILES.get("documento")
        descripcion = limpiar_texto(request.POST.get("descripcion"))

        if not documento:
            messages.error(request, "Debe adjuntar una evidencia de domicilio.")
            return redirect("solicitar_incorporacion")

        extension = os.path.splitext(documento.name)[1].lower()
        nombre_archivo = f"incorporaciones/{vecino.id_vecino}_{uuid.uuid4()}{extension}"

        supabase_storage.storage.from_("documentos-domicilio").upload(
            path=nombre_archivo,
            file=documento.read(),
            file_options={
                "content-type": documento.content_type,
                "upsert": "false"
            }
        )

        documento_url = supabase_storage.storage.from_(
            "documentos-domicilio"
        ).get_public_url(nombre_archivo)

        tipo_solicitud = get_object_or_404(
            Tiposolicitud,
            tipo_solicitud="Incorporación a junta"
        )

        solicitud = Solicitud.objects.create(
            id_solicitud=uuid.uuid4(),
            fecha_solicitud=timezone.now(),
            estado=ESTADO_EN_PROCESO,
            descripcion=descripcion,
            comentario_presidente=None,
            id_vecino=vecino,
            id_tsolicitud=tipo_solicitud
        )

        estado_en_proceso = EstadoSolicitud.objects.get(
            nomb_est_sol=ESTADO_EN_PROCESO
        )

        HistEstSol.objects.create(
            id_solicitud=solicitud,
            id_est=estado_en_proceso,
            fecha_cb_estado=timezone.now()
        )

        SolicitudIncorporacion.objects.create(
            id_solicitud_incorporacion=uuid.uuid4(),
            id_solicitud=solicitud,
            id_junta=junta,
            id_vivienda=vivienda,
            tipo_documento=tipo_documento,
            documento_url=documento_url
        )

        messages.success(request, "Solicitud de incorporación enviada correctamente.")
        return redirect("mis_solicitudes")

    return render(request, "vecino/solicitar_incorporacion.html", {
        "regiones": regiones,
        "comunas": comunas,
        "juntas": juntas,
        "viviendas": viviendas,
    })


@never_cache
@login_required_custom
def mis_datos_view(request):
    vecino = get_object_or_404(
        Vecino,
        id_vecino=request.session.get("vecino_id")
    )

    residencia = obtener_residencia_actual(vecino)
    cargo_actual = obtener_cargo_actual(vecino)

    if request.method == "POST":
        vecino.telefono = limpiar_telefono(request.POST.get("telefono"))

        if request.session.get("rol") == ROL_ADMIN:
            firma = request.FILES.get("firma")

            if firma:
                extension = firma.name.split(".")[-1].lower()
                nombre_archivo = f"presidentes/firma_{vecino.id_vecino}.{extension}"
                archivo_bytes = firma.read()

                supabase_storage.storage.from_("firmas").upload(
                    path=nombre_archivo,
                    file=archivo_bytes,
                    file_options={
                        "content-type": firma.content_type,
                        "upsert": "true"
                    }
                )

                firma_url = supabase_storage.storage.from_("firmas").get_public_url(nombre_archivo)
                vecino.firma_digital = firma_url

        vecino.save()
        messages.success(request, "Datos actualizados correctamente.")
        return redirect("mis_datos")

    return render(request, "mis_datos.html", {
        "vecino": vecino,
        "residencia": residencia,
        "cargo_actual": cargo_actual,
    })


@never_cache
@role_required(ROL_USUARIO)
def solicitar_cambio_domicilio_view(request):
    vecino = get_object_or_404(
        Vecino,
        id_vecino=request.session.get("vecino_id")
    )

    residencia_actual = obtener_residencia_actual(vecino)

    if not residencia_actual:
        messages.error(request, "Actualmente no tienes una vivienda activa.")
        return redirect("mis_datos")

    junta = residencia_actual.id_vivienda.id_junta

    viviendas = Vivienda.objects.filter(
        id_junta=junta
    ).exclude(
        id_vivienda=residencia_actual.id_vivienda.id_vivienda
    ).order_by(
        "nombre_calle",
        "numero_calle"
    )

    if request.method == "POST":
        vivienda_destino = get_object_or_404(
            Vivienda,
            id_vivienda=request.POST.get("id_vivienda_destino"),
            id_junta=junta
        )

        documento = request.FILES.get("documento")

        if not documento:
            messages.error(request, "Debe adjuntar una evidencia de domicilio.")
            return redirect("solicitar_cambio_domicilio")

        extension = os.path.splitext(documento.name)[1].lower()
        nombre_archivo = f"cambios_domicilio/{vecino.id_vecino}_{uuid.uuid4()}{extension}"

        supabase_storage.storage.from_("documentos-domicilio").upload(
            path=nombre_archivo,
            file=documento.read(),
            file_options={
                "content-type": documento.content_type,
                "upsert": "false"
            }
        )

        documento_url = supabase_storage.storage.from_(
            "documentos-domicilio"
        ).get_public_url(nombre_archivo)

        tipo_solicitud = get_object_or_404(
            Tiposolicitud,
            tipo_solicitud="Cambio de domicilio"
        )

        solicitud = Solicitud.objects.create(
            id_solicitud=uuid.uuid4(),
            fecha_solicitud=timezone.now(),
            estado=ESTADO_EN_PROCESO,
            descripcion=limpiar_texto(request.POST.get("descripcion")),
            comentario_presidente=None,
            id_vecino=vecino,
            id_tsolicitud=tipo_solicitud
        )

        estado_en_proceso = EstadoSolicitud.objects.get(
            nomb_est_sol=ESTADO_EN_PROCESO
        )

        HistEstSol.objects.create(
            id_solicitud=solicitud,
            id_est=estado_en_proceso,
            fecha_cb_estado=timezone.now()
        )

        SolicitudCambioDomicilio.objects.create(
            id_solicitud_cambio=uuid.uuid4(),
            id_solicitud=solicitud,
            id_vivienda_destino=vivienda_destino,
            tipo_documento="Evidencia de domicilio",
            documento_url=documento_url
        )

        messages.success(request, "Solicitud de cambio de domicilio enviada correctamente.")
        return redirect("mis_solicitudes")

    return render(request, "vecino/solicitar_cambio_domicilio.html", {
        "residencia_actual": residencia_actual,
        "viviendas": viviendas,
    })


@never_cache
@role_required(ROL_USUARIO)
def mis_solicitudes_view(request):
    vecino = get_object_or_404(
        Vecino,
        id_vecino=request.session.get("vecino_id")
    )

    residencia = obtener_residencia_actual(vecino)

    solicitudes = Solicitud.objects.filter(
        id_vecino=vecino
    ).select_related(
        "id_tsolicitud"
    ).order_by("-fecha_solicitud")

    if not residencia:
        solicitudes = solicitudes.filter(
            id_tsolicitud__tipo_solicitud="Incorporación a junta"
        )

    solicitudes_data = construir_solicitudes_data(solicitudes)

    return render(request, "vecino/mis_solicitudes.html", {
        "solicitudes_data": solicitudes_data,
        "sin_junta": not residencia,
    })


@never_cache
@role_required(ROL_USUARIO)
def crear_solicitud_view(request):
    vecino = get_object_or_404(Vecino, id_vecino=request.session.get("vecino_id"))

    residencia_activa = obtener_residencia_actual(vecino)

    if not residencia_activa:
        messages.error(request, "Debe unirse a una junta para poder crear solicitudes.")
        return redirect("panel_vecino")

    tipos = Tiposolicitud.objects.all()

    if request.method == "POST":
        tipo = get_object_or_404(
            Tiposolicitud,
            id_tsolicitud=request.POST.get("id_tsolicitud")
        )

        solicitud = Solicitud.objects.create(
            id_solicitud=uuid.uuid4(),
            fecha_solicitud=timezone.now(),
            estado=ESTADO_EN_PROCESO,
            descripcion=limpiar_texto(request.POST.get("descripcion")),
            comentario_presidente=None,
            id_vecino=vecino,
            id_tsolicitud=tipo
        )

        estado_en_proceso = EstadoSolicitud.objects.get(
            nomb_est_sol=ESTADO_EN_PROCESO
        )

        HistEstSol.objects.create(
            id_solicitud=solicitud,
            id_est=estado_en_proceso,
            fecha_cb_estado=timezone.now()
        )

        messages.success(request, "Solicitud creada correctamente.")
        return redirect("mis_solicitudes")

    return render(request, "vecino/crear_solicitud.html", {
        "tipos": tipos
    })


@never_cache
@role_required(ROL_USUARIO, ROL_ADMIN)
def vecinos_mi_junta_view(request):
    vecino_actual = get_object_or_404(
        Vecino,
        id_vecino=request.session.get("vecino_id")
    )

    residencia_activa = obtener_residencia_actual(vecino_actual)

    if not residencia_activa:
        messages.error(request, "Debe pertenecer a una junta para ver los vecinos.")

        if request.session.get("rol") == ROL_ADMIN:
            return redirect("panel_presidente")

        return redirect("panel_vecino")

    junta = residencia_activa.id_vivienda.id_junta

    registros = obtener_vecinos_activos_junta(junta)
    vecinos_data = construir_vecinos_data(registros)

    orden_cargos = {
        "Presidente": 1,
        "Secretario": 2,
        "Tesorero": 3,
        "Vecino": 4,
    }

    vecinos_data.sort(
        key=lambda item: (
            orden_cargos.get(item["cargo"], 99),
            item["vecino"].apell_paterno,
            item["vecino"].pri_nombre
        )
    )

    return render(request, "vecinos_junta.html", {
        "junta": junta,
        "vecinos_data": vecinos_data,
        "rol": request.session.get("rol")
    })
    
    
@never_cache
@role_required(ROL_USUARIO, ROL_ADMIN)
def noticias_junta_view(request):
    vecino = get_object_or_404(
        Vecino,
        id_vecino=request.session.get("vecino_id")
    )

    residencia = obtener_residencia_actual(vecino)

    if not residencia:
        messages.error(request, "Debe pertenecer a una junta para ver las noticias.")
        return redireccion_panel(request)

    junta = residencia.id_vivienda.id_junta
    noticias = obtener_noticias_junta(junta)

    return render(request, "noticias_junta.html", {
        "junta": junta,
        "noticias": noticias,
    })