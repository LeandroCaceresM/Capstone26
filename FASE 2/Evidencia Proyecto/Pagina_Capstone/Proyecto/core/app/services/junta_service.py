from app.models import HistVivienda, HistCargo, VecinoDiscap


def obtener_vecinos_activos_junta(junta):
    return HistVivienda.objects.filter(
        id_vivienda__id_junta=junta,
        fecha_ter__isnull=True
    ).select_related("id_vecino", "id_vivienda")


def construir_vecinos_data(registros):
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
            "vivienda": registro.id_vivienda,
            "cargo": cargo_actual.id_cargo.nombre_cargo if cargo_actual else "Vecino",
            "cargo_actual": cargo_actual,
            "condiciones": condiciones
        })

    return vecinos_data