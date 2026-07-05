import uuid
from datetime import date

from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.messages import get_messages
from django.utils import timezone
from django.views.decorators.cache import never_cache

from app.constants import (
    ROL_ADMIN,
    ROL_SUPERADMIN,
    ROL_USUARIO,
    VIGENCIA_ACTIVA,
)
from app.models import Rol, Vecino
from app.supabase_client import supabase
from app.utils import (
    limpiar_correo,
    limpiar_mayusculas,
    limpiar_telefono,
)
from app.validators import (
    es_mayor_16,
    formatear_rut,
    validar_correo,
    validar_nombre_persona,
    validar_rut,
    validar_telefono,
)

# =========================
# AUTENTICACION
# =========================

@never_cache
def registro_view(request):
    fecha_maxima = date.today().replace(year=date.today().year - 16)

    def render_registro(datos=None):
        return render(request, "registro.html", {
            "fecha_maxima": fecha_maxima.isoformat(),
            "datos": datos or {}
        })

    if request.method == "POST":
        datos = request.POST.copy()

        correo = limpiar_correo(request.POST.get("correo"))
        password = request.POST.get("password")

        rut = request.POST.get("rut")
        pri_nombre = limpiar_mayusculas(request.POST.get("pri_nombre"))
        seg_nombre = limpiar_mayusculas(request.POST.get("seg_nombre"))
        apell_paterno = limpiar_mayusculas(request.POST.get("apell_paterno"))
        apell_materno = limpiar_mayusculas(request.POST.get("apell_materno"))
        telefono = limpiar_telefono(request.POST.get("telefono"))
        fecha_de_nacimiento = request.POST.get("fecha_de_nacimiento")
        
        
        if not validar_nombre_persona(pri_nombre):
            messages.error(request, "El primer nombre solo puede contener letras.")
            return render_registro(datos)

        if seg_nombre and not validar_nombre_persona(seg_nombre, obligatorio=False):
            messages.error(request, "El segundo nombre solo puede contener letras.")
            return render_registro(datos)

        if not validar_nombre_persona(apell_paterno):
            messages.error(request, "El apellido paterno solo puede contener letras.")
            return render_registro(datos)

        if not validar_nombre_persona(apell_materno):
            messages.error(request, "El apellido materno solo puede contener letras.")
            return render_registro(datos)        
        

        if not validar_correo(correo):
            messages.error(
                request,
                "Ingrese un correo válido. Debe contener @ y terminar en .com o .cl."
            )
            return render_registro(datos)

        if not validar_telefono(telefono):
            messages.error(request, "Ingrese un número de teléfono válido de 8 o 9 dígitos.")
            return render_registro(datos)

        if not es_mayor_16(fecha_de_nacimiento):
            messages.error(request, "Debes tener al menos 16 años para registrarte.")
            return render_registro(datos)

        if not validar_rut(rut):
            messages.error(request, "El RUT ingresado no es válido.")
            return render_registro(datos)

        rut = formatear_rut(rut)

        if Vecino.objects.filter(rut=rut).exists():
            messages.error(request, "Ya existe un usuario registrado con ese RUT.")
            return render_registro(datos)

        if Vecino.objects.filter(correo=correo).exists():
            messages.error(request, "Ya existe un usuario registrado con ese correo.")
            return render_registro(datos)

        try:
            auth_response = supabase.auth.sign_up({
                "email": correo,
                "password": password
            })

            user = auth_response.user

            if not user:
                messages.error(request, "No se pudo crear el usuario.")
                return render_registro(datos)

            rol_vecino = Rol.objects.get(nombre_rol=ROL_USUARIO)

            Vecino.objects.create(
                id_vecino=uuid.uuid4(),
                supabase_uid=user.id,
                rut=rut,
                pri_nombre=pri_nombre,
                seg_nombre=seg_nombre,
                apell_paterno=apell_paterno,
                apell_materno=apell_materno,
                correo=correo,
                telefono=telefono,
                fecha_de_nacimiento=fecha_de_nacimiento,
                vigencia=VIGENCIA_ACTIVA,
                fecha_registro=timezone.now(),
                id_rol=rol_vecino
            )

            messages.success(request, "Registro exitoso. Ahora puedes iniciar sesión.")
            return redirect("login")

        except Exception as e:
            messages.error(request, f"Error al registrar: {e}")
            return render_registro(datos)

    return render_registro()


@never_cache
def login_view(request):
    if request.method == "POST":
        correo = limpiar_correo(request.POST.get("correo"))
        password = request.POST.get("password")

        try:
            auth_response = supabase.auth.sign_in_with_password({
                "email": correo,
                "password": password
            })

            user = auth_response.user

            if not user:
                messages.error(request, "Correo o contraseña incorrectos.")
                return redirect("login")

            vecino = Vecino.objects.get(supabase_uid=user.id)
                        
            if vecino.vigencia != VIGENCIA_ACTIVA:
                request.session.flush()
                messages.error(
                    request,
                    "Tu cuenta se encuentra inactiva. Contacta al administrador del sistema."
                )
                return redirect("login")
            
            if not Vecino.objects.filter(correo=correo).exists():
                messages.error(request, "No existe una cuenta registrada con ese correo.")
                return redirect("login")

            if not validar_correo(correo):
                messages.error(
                    request,
                    "Ingrese un correo válido. Debe contener @ y terminar en .com o .cl."
                )
                return redirect("login")

            request.session["supabase_uid"] = str(user.id)
            request.session["vecino_id"] = str(vecino.id_vecino)
            request.session["nombre"] = vecino.pri_nombre
            request.session["rol"] = vecino.id_rol.nombre_rol

            rol = vecino.id_rol.nombre_rol

            if rol == ROL_USUARIO:
                return redirect("panel_vecino")

            elif rol == ROL_ADMIN:
                return redirect("panel_presidente")

            elif rol == ROL_SUPERADMIN:
                return redirect("panel_superadmin")

            else:
                messages.error(request, "Rol no reconocido.")
                return redirect("login")

        except Vecino.DoesNotExist:
            messages.error(request, "El usuario existe en Auth, pero no está registrado como vecino.")
            return redirect("login")

        except Exception as e:
            messages.error(request, f"Error al iniciar sesión: {e}")
            return redirect("login")

    return render(request, "login.html")


@never_cache
def logout_view(request):
    storage = get_messages(request)
    for _ in storage:
        pass

    request.session.flush()
    messages.success(request, "Sesión cerrada correctamente.")
    return redirect("login")


# =========================
# RECUPERAR CONTRASEÑA
# =========================

@never_cache
def recuperar_contrasenia(request):
    return render(request, "recuperar_contrasenia.html")


@never_cache
def enviar_recuperacion(request):
    if request.method == "POST":
        correo = limpiar_correo(request.POST.get("correo"))

        if not validar_correo(correo):
            messages.error(
                request,
                "Ingrese un correo válido. Debe contener @ y terminar en .com o .cl."
            )
            return redirect("recuperar_contrasenia")

        if not Vecino.objects.filter(correo=correo, vigencia="S").exists():
            messages.error(
                request,
                "No existe una cuenta activa registrada con ese correo."
            )
            return redirect("recuperar_contrasenia")

        try:
            supabase.auth.reset_password_email(
                correo,
                {
                    "redirect_to": "http://127.0.0.1:8000/cambiar_contrasenia/"
                }
            )

            messages.success(
                request,
                "Revisa tu correo para cambiar la contraseña."
            )

        except Exception as e:
            messages.error(
                request,
                f"Error al enviar recuperación: {e}"
            )

    return redirect("recuperar_contrasenia")


@never_cache
def cambiar_contrasenia(request):
    access_token = request.GET.get("access_token")
    refresh_token = request.GET.get("refresh_token")

    if access_token and refresh_token:
        try:
            supabase.auth.set_session(
                access_token,
                refresh_token
            )

        except Exception as e:
            messages.error(
                request,
                f"Error creando sesión: {e}"
            )

    if request.method == "POST":
        password = request.POST.get("password")

        if not password or len(password) < 6:
            messages.error(
                request,
                "La contraseña debe tener al menos 6 caracteres."
            )
            return redirect("cambiar_contrasenia")

        try:
            supabase.auth.update_user({
                "password": password
            })

            messages.success(
                request,
                "Contraseña actualizada correctamente."
            )

            return redirect("login")

        except Exception as e:
            messages.error(
                request,
                f"Error al cambiar contraseña: {e}"
            )

    return render(request, "cambiar_contrasenia.html")