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

@never_cache
def generar_certificado_view(request):

    if not request.session.get("vecino_id"):
        return redirect("login")

    if request.session.get("rol") not in ["Usuario", "Admin"]:
        messages.error(request, "No tienes permiso para generar certificados.")
        return redirect("login")   

    vecino = get_object_or_404(Vecino, id_vecino=request.session.get("vecino_id"))

    residencia = HistVivienda.objects.filter(
        id_vecino=vecino,
        fecha_ter__isnull=True
    ).select_related(
        "id_vivienda__id_junta",
        "id_vivienda__id_junta__id_comuna",
        "id_vivienda__id_junta__id_comuna__id_region"
    ).first()

    if not residencia:
        messages.error(request, "Debe pertenecer a una junta para generar el certificado.")
        return redirect("panel_vecino")

    junta = residencia.id_vivienda.id_junta
    vivienda = residencia.id_vivienda
    comuna = junta.id_comuna.nom_comuna

    presidente_cargo = HistCargo.objects.filter(
        id_directiva__id_junta=junta,
        id_cargo__nombre_cargo__iexact="Presidente",
        fecha_cargo_fin_real__isnull=True
    ).select_related("id_vecino").first()

    if not presidente_cargo:
        messages.error(request, "La junta aún no tiene presidente asignado.")
        return redirect("panel_vecino")

    presidente = presidente_cargo.id_vecino

    if not presidente.firma_digital:
        messages.error(request, "El presidente aún no ha subido su firma digital.")
        return redirect("panel_vecino")

    hoy = timezone.localtime(timezone.now()).date()
    anio = hoy.year

    certificado = CertificadoDeResidencia.objects.filter(
        id_vecino=vecino,
        id_vecino2=presidente,
        fecha_emision__date=hoy
    ).first()

    if certificado:
        numero_certificado = certificado.numero_certificado
    else:
        correlativo = CertificadoDeResidencia.objects.filter(
            fecha_emision__year=anio
        ).count() + 1

        numero_certificado = f"CERT-{anio}-{correlativo:04d}"

        certificado = CertificadoDeResidencia.objects.create(
            id_certificado=uuid.uuid4(),
            numero_certificado=numero_certificado,
            fecha_emision=timezone.now(),
            id_vecino=vecino,
            id_vecino2=presidente
        )

    carpeta_certificados = os.path.join(settings.MEDIA_ROOT, "certificados")
    os.makedirs(carpeta_certificados, exist_ok=True)

    nombre_pdf = f"{numero_certificado}_{vecino.id_vecino}.pdf"
    ruta_pdf = os.path.join(carpeta_certificados, nombre_pdf)

    meses = {
        1: "enero", 2: "febrero", 3: "marzo", 4: "abril",
        5: "mayo", 6: "junio", 7: "julio", 8: "agosto",
        9: "septiembre", 10: "octubre", 11: "noviembre", 12: "diciembre",
    }

    fecha_formal = f"{comuna}, {hoy.day} de {meses[hoy.month]} de {hoy.year}"

    direccion = f"{vivienda.nombre_calle} N° {vivienda.numero_calle}"

    if vivienda.tipo_vivienda == "D":
        direccion += f", Block {vivienda.num_block}, Departamento {vivienda.num_dpto}"

    direccion += f", comuna de {comuna}"

    c = canvas.Canvas(ruta_pdf, pagesize=letter)
    width, height = letter

    x_left = 80
    y = height - 60

    c.setFont("Helvetica", 9)
    c.drawRightString(width - 70, y, numero_certificado)

    y -= 35
    c.setFont("Helvetica-Bold", 13)
    c.drawCentredString(width / 2, y, "JUNTA DE VECINOS")
    y -= 18
    c.setFont("Helvetica-Bold", 14)
    c.drawCentredString(width / 2, y, f"“{junta.nombre.upper()}”")
    y -= 18
    c.setFont("Helvetica", 11)
    c.drawCentredString(width / 2, y, "UrbanLink")

    y -= 65
    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(width / 2, y, "CERTIFICADO DE RESIDENCIA")
    c.line(width / 2 - 125, y - 5, width / 2 + 125, y - 5)

    y -= 50
    c.setFont("Helvetica", 11)
    c.drawRightString(width - 80, y, fecha_formal)

    y -= 55
    c.setFont("Helvetica", 12)

    lineas = [
        f"Quien suscribe, Presidente de la Junta de Vecinos “{junta.nombre}”,",
        "certifica mediante el presente documento que:",
        "",
        f"Don(a): {vecino.pri_nombre} {vecino.apell_paterno} {vecino.apell_materno}",
        f"RUT N°: {vecino.rut}",
        f"Registra domicilio en: {direccion}.",
        "",
        "El presente certificado se extiende a petición del interesado(a),",
        "para los fines que estime pertinente.",
    ]

    for linea in lineas:
        if linea == "":
            y -= 15
        else:
            c.drawString(x_left, y, linea)
            y -= 25

    y -= 90

    try:
        respuesta = requests.get(presidente.firma_digital, timeout=10)

        if respuesta.status_code == 200:
            firma_img = ImageReader(BytesIO(respuesta.content))
            c.drawImage(
                firma_img,
                width / 2 - 90,
                y,
                width=180,
                height=70,
                preserveAspectRatio=True,
                mask="auto"
            )
    except Exception:
        pass

    y -= 25
    c.line(width / 2 - 120, y, width / 2 + 120, y)

    y -= 18
    c.setFont("Helvetica-Bold", 11)
    c.drawCentredString(
        width / 2,
        y,
        f"{presidente.pri_nombre.upper()} {presidente.apell_paterno.upper()} {presidente.apell_materno.upper()}"
    )

    y -= 16
    c.setFont("Helvetica", 10)
    c.drawCentredString(width / 2, y, f"PRESIDENTE JJ.VV. “{junta.nombre.upper()}”")

    c.setFont("Helvetica", 9)
    c.drawCentredString(width / 2, 50, "Documento emitido digitalmente a través de UrbanLink.")

    c.save()

    return FileResponse(
        open(ruta_pdf, "rb"),
        as_attachment=True,
        filename=f"{numero_certificado}_certificado_residencia.pdf"
    )
    
