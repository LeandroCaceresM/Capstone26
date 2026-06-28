import os
import uuid
import requests

from io import BytesIO

from django.conf import settings
from django.utils import timezone
from django.http import FileResponse

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.utils import ImageReader

from app.models import (
    HistVivienda,
    HistCargo,
    CertificadoDeResidencia,
)


MESES = {
    1: "enero",
    2: "febrero",
    3: "marzo",
    4: "abril",
    5: "mayo",
    6: "junio",
    7: "julio",
    8: "agosto",
    9: "septiembre",
    10: "octubre",
    11: "noviembre",
    12: "diciembre",
}


def obtener_residencia_actual(vecino):
    return HistVivienda.objects.filter(
        id_vecino=vecino,
        fecha_ter__isnull=True
    ).select_related(
        "id_vivienda__id_junta",
        "id_vivienda__id_junta__id_comuna",
        "id_vivienda__id_junta__id_comuna__id_region"
    ).first()


def obtener_presidente_junta(junta):
    presidente_cargo = HistCargo.objects.filter(
        id_directiva__id_junta=junta,
        id_cargo__nombre_cargo__iexact="Presidente",
        fecha_cargo_fin_real__isnull=True
    ).select_related("id_vecino").first()

    if presidente_cargo:
        return presidente_cargo.id_vecino

    return None


def obtener_o_crear_certificado(vecino, presidente):
    hoy = timezone.localtime(timezone.now()).date()
    anio = hoy.year

    certificado = CertificadoDeResidencia.objects.filter(
        id_vecino=vecino,
        id_vecino2=presidente,
        fecha_emision__date=hoy
    ).first()

    if certificado:
        return certificado

    correlativo = CertificadoDeResidencia.objects.filter(
        fecha_emision__year=anio
    ).count() + 1

    numero_certificado = f"CERT-{anio}-{correlativo:04d}"

    return CertificadoDeResidencia.objects.create(
        id_certificado=uuid.uuid4(),
        numero_certificado=numero_certificado,
        fecha_emision=timezone.now(),
        id_vecino=vecino,
        id_vecino2=presidente
    )


def fecha_formal(fecha, comuna):
    return f"{comuna}, {fecha.day} de {MESES[fecha.month]} de {fecha.year}"


def direccion_completa(vivienda, comuna):
    direccion = f"{vivienda.nombre_calle} N° {vivienda.numero_calle}"

    if vivienda.tipo_vivienda == "D":
        direccion += f", Block {vivienda.num_block}, Departamento {vivienda.num_dpto}"

    direccion += f", comuna de {comuna}"

    return direccion


def generar_pdf_certificado(vecino, residencia, presidente, certificado):
    hoy = timezone.localtime(certificado.fecha_emision).date()

    junta = residencia.id_vivienda.id_junta
    vivienda = residencia.id_vivienda
    comuna = junta.id_comuna.nom_comuna

    numero_certificado = certificado.numero_certificado
    fecha_texto = fecha_formal(hoy, comuna)
    direccion = direccion_completa(vivienda, comuna)

    carpeta_certificados = os.path.join(settings.MEDIA_ROOT, "certificados")
    os.makedirs(carpeta_certificados, exist_ok=True)

    nombre_pdf = f"{numero_certificado}_{vecino.id_vecino}.pdf"
    ruta_pdf = os.path.join(carpeta_certificados, nombre_pdf)

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
    c.drawRightString(width - 80, y, fecha_texto)

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
    c.drawCentredString(
        width / 2,
        y,
        f"PRESIDENTE JJ.VV. “{junta.nombre.upper()}”"
    )

    c.setFont("Helvetica", 9)
    c.drawCentredString(
        width / 2,
        50,
        "Documento emitido digitalmente a través de UrbanLink."
    )

    c.save()

    return ruta_pdf, f"{numero_certificado}_certificado_residencia.pdf"


def crear_respuesta_pdf(ruta_pdf, nombre_descarga):
    return FileResponse(
        open(ruta_pdf, "rb"),
        as_attachment=True,
        filename=nombre_descarga
    )