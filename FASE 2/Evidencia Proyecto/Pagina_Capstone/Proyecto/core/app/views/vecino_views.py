import uuid
import os
import requests

from datetime import date
from io import BytesIO

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.conf import settings
from django.http import FileResponse
from django.db import models

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.utils import ImageReader

from app.models import *
from app.supabase_client import supabase
from app.supabase_storage_client import supabase_storage
from app.utils import *
from app.validators import *

# =========================
# VISTAS VECINO
# =========================

@never_cache
def panel_vecino_view(request):
    if not request.session.get("vecino_id"):
        return redirect("login")

    if request.session.get("rol") != "Usuario":
        messages.error(request, "No tienes permiso para entrar a esa sección.")
        return redirect("login")

    vecino = get_object_or_404(Vecino, id_vecino=request.session.get("vecino_id"))

    residencia = HistVivienda.objects.filter(
        id_vecino=vecino,
        fecha_ter__isnull=True
    ).select_related("id_vivienda__id_junta").first()

    cargo_actual = HistCargo.objects.filter(
        id_vecino=vecino,
        fecha_cargo_fin_real__isnull=True
    ).select_related("id_cargo").first()

    solicitudes_en_proceso = Solicitud.objects.filter(
        id_vecino=vecino,
        estado="EN PROCESO"
    ).count()

    solicitudes_aprobadas = Solicitud.objects.filter(
        id_vecino=vecino,
        estado="APROBADO"
    ).count()

    solicitudes_rechazadas = Solicitud.objects.filter(
        id_vecino=vecino,
        estado="RECHAZADO"
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
def mis_solicitudes_view(request):
    if not request.session.get("vecino_id"):
        return redirect("login")

    vecino = get_object_or_404(Vecino, id_vecino=request.session.get("vecino_id"))

    residencia_activa = HistVivienda.objects.filter(
        id_vecino=vecino,
        fecha_ter__isnull=True
    ).first()

    if not residencia_activa:
        messages.error(request, "Debe unirse a una junta para poder usar las solicitudes.")
        return redirect("panel_vecino")

    solicitudes = Solicitud.objects.filter(
        id_vecino=vecino
    ).select_related("id_tsolicitud").order_by("-fecha_solicitud")

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

    return render(request, "vecino/mis_solicitudes.html", {
        "solicitudes_data": solicitudes_data
    })

@never_cache
def crear_solicitud_view(request):
    if not request.session.get("vecino_id"):
        return redirect("login")

    vecino = get_object_or_404(Vecino, id_vecino=request.session.get("vecino_id"))

    residencia_activa = HistVivienda.objects.filter(
        id_vecino=vecino,
        fecha_ter__isnull=True
    ).first()

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
            estado="EN PROCESO",
            descripcion = limpiar_texto(request.POST.get("descripcion")),
            comentario_presidente=None,
            id_vecino=vecino,
            id_tsolicitud=tipo
        )

        estado_en_proceso = EstadoSolicitud.objects.get(nomb_est_sol="EN PROCESO")

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


# =========================
# SERVICIOS GENERALES
# =========================

@never_cache
def mis_datos_view(request):
    if not request.session.get("vecino_id"):
        return redirect("login")

    vecino = get_object_or_404(Vecino, id_vecino=request.session.get("vecino_id"))

    cargo_actual = HistCargo.objects.filter(
        id_vecino=vecino,
        fecha_cargo_fin_real__isnull=True
    ).select_related("id_cargo").first()

    if request.method == "POST":
        vecino.telefono = request.POST.get("telefono")

        if request.session.get("rol") == "Admin":
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
def vecinos_mi_junta_view(request):
    if not request.session.get("vecino_id"):
        return redirect("login")

    if request.session.get("rol") not in ["Usuario", "Admin"]:
        messages.error(request, "No tienes permiso para ver esta sección.")
        return redirect("login")

    vecino_actual = get_object_or_404(
        Vecino,
        id_vecino=request.session.get("vecino_id")
    )

    residencia_activa = HistVivienda.objects.filter(
        id_vecino=vecino_actual,
        fecha_ter__isnull=True
    ).select_related("id_vivienda__id_junta").first()

    if not residencia_activa:
        messages.error(request, "Debe pertenecer a una junta para ver los vecinos.")
        if request.session.get("rol") == "Admin":
            return redirect("panel_presidente")
        return redirect("panel_vecino")

    junta = residencia_activa.id_vivienda.id_junta

    registros = HistVivienda.objects.filter(
        id_vivienda__id_junta=junta,
        fecha_ter__isnull=True
    ).select_related("id_vecino", "id_vivienda")

    vecinos_data = []

    for registro in registros:
        cargo_actual = HistCargo.objects.filter(
            id_vecino=registro.id_vecino,
            fecha_cargo_fin_real__isnull=True
        ).select_related("id_cargo").first()

        condiciones = VecinoDiscap.objects.filter(
            id_vecino=registro.id_vecino
        ).select_related("id_tipo_discap")

        vecinos_data.append({
            "vecino": registro.id_vecino,
            "cargo": cargo_actual.id_cargo.nombre_cargo if cargo_actual else "Vecino",
            "condiciones": condiciones
        })

    return render(request, "vecinos_junta.html", {
        "junta": junta,
        "vecinos_data": vecinos_data,
        "rol": request.session.get("rol")
    })
