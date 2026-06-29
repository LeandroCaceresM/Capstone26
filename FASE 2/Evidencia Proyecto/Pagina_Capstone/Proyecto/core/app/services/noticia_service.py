from app.constants import VIGENCIA_ACTIVA
from app.models import Noticia


def obtener_noticias_junta(junta):
    return Noticia.objects.filter(
        id_junta=junta,
        vigencia=VIGENCIA_ACTIVA
    ).select_related("id_vecino").order_by("-fecha_publicacion")


def obtener_ultimas_noticias_junta(junta, limite=3):
    return obtener_noticias_junta(junta)[:limite]