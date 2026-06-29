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
from app.services.noticia_service import obtener_noticias_junta

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
    })


@never_cache
@role_required(ROL_USUARIO)
def mis_solicitudes_view(request):
    vecino = get_object_or_404(Vecino, id_vecino=request.session.get("vecino_id"))

    residencia_activa = obtener_residencia_actual(vecino)

    if not residencia_activa:
        messages.error(request, "Debe unirse a una junta para poder usar las solicitudes.")
        return redirect("panel_vecino")

    solicitudes = Solicitud.objects.filter(
        id_vecino=vecino
    ).select_related("id_tsolicitud").order_by("-fecha_solicitud")

    solicitudes_data = construir_solicitudes_data(solicitudes)

    return render(request, "vecino/mis_solicitudes.html", {
        "solicitudes_data": solicitudes_data
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
@login_required_custom
def mis_datos_view(request):
    vecino = get_object_or_404(Vecino, id_vecino=request.session.get("vecino_id"))

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
        "cargo_actual": cargo_actual,
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