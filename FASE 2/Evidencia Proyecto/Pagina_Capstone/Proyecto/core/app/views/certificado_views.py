from django.shortcuts import redirect, get_object_or_404
from django.contrib import messages
from django.views.decorators.cache import never_cache

from app.models import Vecino
from app.decorators import role_required

from app.services.certificado_service import (
    obtener_residencia_actual,
    obtener_presidente_junta,
    obtener_o_crear_certificado,
    generar_pdf_certificado,
    crear_respuesta_pdf,
)

@never_cache
def generar_certificado_view(request):
    if not request.session.get("vecino_id"):
        return redirect("login")

    if request.session.get("rol") not in ["Usuario", "Admin"]:
        messages.error(request, "No tienes permiso para generar certificados.")
        return redirect("login")

    vecino = get_object_or_404(Vecino, id_vecino=request.session.get("vecino_id"))

    residencia = obtener_residencia_actual(vecino)

    if not residencia:
        messages.error(request, "Debe pertenecer a una junta para generar el certificado.")

        if request.session.get("rol") == "Admin":
            return redirect("panel_presidente")

        return redirect("panel_vecino")

    junta = residencia.id_vivienda.id_junta

    presidente = obtener_presidente_junta(junta)

    if not presidente:
        messages.error(request, "La junta aún no tiene presidente asignado.")

        if request.session.get("rol") == "Admin":
            return redirect("panel_presidente")

        return redirect("panel_vecino")

    if not presidente.firma_digital:
        messages.error(request, "El presidente aún no ha subido su firma digital.")

        if request.session.get("rol") == "Admin":
            return redirect("panel_presidente")

        return redirect("panel_vecino")

    certificado = obtener_o_crear_certificado(vecino, presidente)

    ruta_pdf, nombre_descarga = generar_pdf_certificado(
        vecino,
        residencia,
        presidente,
        certificado
    )

    return crear_respuesta_pdf(ruta_pdf, nombre_descarga)
