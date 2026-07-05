import re

from datetime import date

# =========================
# Validaciones para Registro
# =========================

# =========================
# NOMBRE DE VECINO
# =========================

def validar_nombre_persona(texto, obligatorio=True):
    if not texto:
        return not obligatorio

    texto = texto.strip()

    patron = r"^[A-Za-zÁÉÍÓÚáéíóúÑñ\s'-]+$"

    tiene_letra = re.search(r"[A-Za-zÁÉÍÓÚáéíóúÑñ]", texto)

    return (
        re.fullmatch(patron, texto) is not None
        and tiene_letra is not None
    )

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

# =========================
# Correo
# =========================

def validar_correo(correo):        

    if not correo:
        return False

    patron = r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.(com|cl)$"
    return re.match(patron, correo) is not None

# =========================
# Contaseña
# =========================

def validar_password(password):
    if not password:
        return False, "Debe ingresar una contraseña."

    if len(password) < 8:
        return False, "La contraseña debe tener al menos 8 caracteres."

    if not re.search(r"[A-Za-z]", password):
        return False, "La contraseña debe contener al menos una letra."

    if not re.search(r"\d", password):
        return False, "La contraseña debe contener al menos un número."

    comunes = {
        "12345678",
        "123456789",
        "password",
        "qwerty",
        "asdfghj",
        "admin123",
        "123123123",
        "abcdefgh"
    }

    if password.lower() in comunes:
        return False, "La contraseña es demasiado común."

    return True, ""