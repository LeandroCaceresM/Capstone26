import re

# ==================================================
# FUNCIONES DE NORMALIZACIÓN
# ==================================================

def limpiar_texto(texto):
# Elimina espacios repetidos y espacios al inicio/final.

    if texto is None:
        return None

    texto = re.sub(r"\s+", " ", texto.strip())

    return texto

def limpiar_mayusculas(texto):
# Elimina espacios repetidos y convierte a MAYÚSCULAS.

    texto = limpiar_texto(texto)

    if texto:
        return texto.upper()

    return None

def limpiar_correo(correo):
    correo = limpiar_texto(correo)

    if correo:
        return correo.lower()

    return None

def limpiar_telefono(telefono):
    if not telefono:
        return None

    # Deja solo números
    telefono = re.sub(r"\D", "", telefono)

    return telefono

def limpiar_titulo(texto):
    
    texto = limpiar_texto(texto)

    if texto:
        return texto.title()

    return None
