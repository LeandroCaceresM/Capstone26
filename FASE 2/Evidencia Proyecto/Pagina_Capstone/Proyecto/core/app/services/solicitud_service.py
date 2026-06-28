from app.models import HistEstSol


def obtener_fecha_cierre_solicitud(solicitud):
    hist_cierre = HistEstSol.objects.filter(
        id_solicitud=solicitud,
        id_est__nomb_est_sol__in=["APROBADO", "RECHAZADO"]
    ).order_by("-fecha_cb_estado").first()

    return hist_cierre.fecha_cb_estado if hist_cierre else None


def construir_solicitudes_data(solicitudes):
    data = []

    for solicitud in solicitudes:
        data.append({
            "solicitud": solicitud,
            "fecha_resuelta": obtener_fecha_cierre_solicitud(solicitud)
        })

    return data