import re

from datetime import date

# =========================
# Validaciones para Registro
# =========================

# =========================
# RUT
# =========================

def limpiar_rut(rut):
    return rut.upper().replace(".", "").replace("-", "").strip()

def validar_rut(rut):
    rut = limpiar_rut(rut)

    if not re.match(r"^\d+[0-9K]$", rut):
        return False

    cuerpo = rut[:-1]
    dv = rut[-1]

    suma = 0
    multiplicador = 2

    for digito in reversed(cuerpo):
        suma += int(digito) * multiplicador
        multiplicador += 1

        if multiplicador > 7:
            multiplicador = 2

    resto = 11 - (suma % 11)

    if resto == 11:
        dv_calculado = "0"
    elif resto == 10:
        dv_calculado = "K"
    else:
        dv_calculado = str(resto)

    return dv == dv_calculado

def formatear_rut(rut):
    rut = limpiar_rut(rut)

    cuerpo = rut[:-1]
    dv = rut[-1]

    cuerpo_formateado = f"{int(cuerpo):,}".replace(",", ".")

    return f"{cuerpo_formateado}-{dv}"

# =========================
# Fecha de nacimiento
# =========================

def es_mayor_16(fecha_nacimiento):
    """
    Recibe una fecha en formato YYYY-MM-DD.
    Retorna True si tiene 16 años o más.
    """

    nacimiento = date.fromisoformat(fecha_nacimiento)
    hoy = date.today()

    edad = hoy.year - nacimiento.year

    if (hoy.month, hoy.day) < (nacimiento.month, nacimiento.day):
        edad -= 1

    return edad >= 16

# =========================
# Telefono (limitar de 8 a 9 digitos)
# =========================

def validar_telefono(telefono):
    return telefono.isdigit() and 8 <= len(telefono) <= 9