from django.utils import timezone

from app.constants import VIGENCIA_ACTIVA
from app.models import Evento


def obtener_eventos_junta(junta):
    return Evento.objects.filter(
        id_junta=junta,
        vigencia=VIGENCIA_ACTIVA
    ).select_related("id_vecino").order_by("fecha_evento")


def obtener_proximos_eventos_junta(junta, limite=3):
    return Evento.objects.filter(
        id_junta=junta,
        vigencia=VIGENCIA_ACTIVA,
        fecha_evento__gte=timezone.now()
    ).order_by("fecha_evento")[:limite]