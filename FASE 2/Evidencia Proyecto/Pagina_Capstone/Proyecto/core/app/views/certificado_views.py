from django.shortcuts import render, get_object_or_404
from django.contrib import messages
from django.views.decorators.cache import never_cache

from app.constants import ROL_ADMIN, ROL_USUARIO
from app.models import Vecino, CertificadoDeResidencia
from app.decorators import role_required
from app.services.vecino_service import obtener_cargo_actual
from app.utils import redireccion_panel

from app.services.certificado_service import (
    obtener_residencia_actual,
    obtener_presidente_junta,
    obtener_o_crear_certificado,
    generar_pdf_certificado,
    crear_respuesta_pdf,
)

@never_cache
@role_required(ROL_USUARIO, ROL_ADMIN)
def certificado_residencia_view(request):
    vecino = get_object_or_404(
        Vecino,
        id_vecino=request.session.get("vecino_id")
    )
    
    residencia = obtener_residencia_actual(vecino)

    if not residencia:
        messages.error(request, "Debe pertenecer a una junta para poder solicitar el certificado.")
        return redireccion_panel(request)

    residencia = obtener_residencia_actual(vecino)
    cargo = obtener_cargo_actual(vecino)

    direccion = "Sin residencia registrada"
    firma_disponible = False

    if residencia:
        vivienda = residencia.id_vivienda
        junta = vivienda.id_junta

        direccion = f"{vivienda.nombre_calle} {vivienda.numero_calle}"

        if vivienda.tipo_vivienda == "D":
            direccion += f", Block {vivienda.num_block}, Depto {vivienda.num_dpto}"

        presidente = obtener_presidente_junta(junta)

        if presidente and presidente.firma_digital:
            firma_disponible = True

    cargo_actual = cargo.id_cargo.nombre_cargo if cargo else "Vecino"

    certificados_emitidos = None

    if request.session.get("rol") == ROL_ADMIN:
        certificados_emitidos = CertificadoDeResidencia.objects.filter(
            id_vecino2=vecino
        ).select_related("id_vecino").order_by("-fecha_emision")

    return render(request, "certificado_residencia.html", {
        "vecino": vecino,
        "direccion": direccion,
        "cargo_actual": cargo_actual,
        "firma_disponible": firma_disponible,
        "certificados_emitidos": certificados_emitidos,
    })
    
    
@never_cache
@role_required(ROL_USUARIO, ROL_ADMIN)
def generar_certificado_view(request):
    vecino = get_object_or_404(
        Vecino,
        id_vecino=request.session.get("vecino_id")
    )

    residencia = obtener_residencia_actual(vecino)

    if not residencia:
        messages.error(
            request,
            "Debe pertenecer a una junta para generar el certificado."
        )
        return redireccion_panel(request)

    presidente = obtener_presidente_junta(
        residencia.id_vivienda.id_junta
    )

    if not presidente:
        messages.error(
            request,
            "La junta aún no tiene presidente asignado."
        )
        return redireccion_panel(request)

    if not presidente.firma_digital:
        messages.error(
            request,
            "El presidente aún no ha subido su firma digital."
        )
        return redireccion_panel(request)

    certificado = obtener_o_crear_certificado(vecino, presidente)

    ruta_pdf, nombre_descarga = generar_pdf_certificado(
        vecino,
        residencia,
        presidente,
        certificado
    )

    return crear_respuesta_pdf(ruta_pdf, nombre_descarga)