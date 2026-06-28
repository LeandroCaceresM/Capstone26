from app.models import HistVivienda, HistCargo, VecinoDiscap


def obtener_residencia_actual(vecino):
    return HistVivienda.objects.filter(
        id_vecino=vecino,
        fecha_ter__isnull=True
    ).select_related("id_vivienda__id_junta").first()


def obtener_cargo_actual(vecino):
    return HistCargo.objects.filter(
        id_vecino=vecino,
        fecha_cargo_fin_real__isnull=True
    ).select_related("id_cargo").first()


def obtener_condiciones_vecino(vecino):
    return VecinoDiscap.objects.filter(
        id_vecino=vecino
    ).select_related("id_tipo_discap")