# =========================
# IMPORTS
# =========================
import uuid
import os
import requests
import re

from io import BytesIO

from .utils import *
from .validators import *

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.messages import get_messages
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.conf import settings
from django.http import FileResponse
from django.db import models

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.utils import ImageReader

from .models import *
from .supabase_client import supabase
from .supabase_storage_client import supabase_storage



# =========================
# AUTENTICACION
# =========================

@never_cache
def registro_view(request):
    fecha_maxima = date.today().replace(year=date.today().year - 16)

    if request.method == "POST":
        correo = limpiar_correo(request.POST.get("correo"))
        password = request.POST.get("password")

        rut = request.POST.get("rut")
        pri_nombre = limpiar_mayusculas(request.POST.get("pri_nombre"))
        seg_nombre = limpiar_mayusculas(request.POST.get("seg_nombre"))
        apell_paterno = limpiar_mayusculas(request.POST.get("apell_paterno"))
        apell_materno = limpiar_mayusculas(request.POST.get("apell_materno"))
        telefono = limpiar_telefono(request.POST.get("telefono"))
        fecha_de_nacimiento = request.POST.get("fecha_de_nacimiento")

        if not es_mayor_16(fecha_de_nacimiento):
            messages.error(request, "Debes tener al menos 16 años para registrarte.")
            return redirect("registro")

        if not validar_rut(rut):
            messages.error(request, "El RUT ingresado no es válido.")
            return redirect("registro")

        rut = formatear_rut(rut)

        if Vecino.objects.filter(rut=rut).exists():
            messages.error(request, "Ya existe un usuario registrado con ese RUT.")
            return redirect("registro")

        if Vecino.objects.filter(correo=correo).exists():
            messages.error(request, "Ya existe un usuario registrado con ese correo.")
            return redirect("registro")

        try:
            auth_response = supabase.auth.sign_up({
                "email": correo,
                "password": password
            })

            user = auth_response.user

            if not user:
                messages.error(request, "No se pudo crear el usuario.")
                return redirect("registro")

            rol_vecino = Rol.objects.get(nombre_rol="Usuario")

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
                vigencia="S",
                fecha_registro=timezone.now(),
                id_rol=rol_vecino
            )

            messages.success(request, "Registro exitoso. Ahora puedes iniciar sesión.")
            return redirect("login")

        except Exception as e:
            messages.error(request, f"Error al registrar: {e}")
            return redirect("registro")

    return render(request, "registro.html", {
        "fecha_maxima": fecha_maxima.isoformat()
    })

@never_cache
def login_view(request):
    if request.method == "POST":
        correo = request.POST.get("correo")
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
                        
            if vecino.vigencia != "S":
                request.session.flush()
                messages.error(
                    request,
                    "Tu cuenta se encuentra inactiva. Contacta al administrador del sistema."
                )
                return redirect("login")

            request.session["supabase_uid"] = str(user.id)
            request.session["vecino_id"] = str(vecino.id_vecino)
            request.session["nombre"] = vecino.pri_nombre
            request.session["rol"] = vecino.id_rol.nombre_rol

            rol = vecino.id_rol.nombre_rol

            if rol == "Usuario":
                return redirect("panel_vecino")

            elif rol == "Admin":
                return redirect("panel_presidente")

            elif rol == "Superadmin":
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
        correo = request.POST.get("correo")
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
    return render(
        request,
        "cambiar_contrasenia.html"
    )


# =========================
# SERVICIOS GENERALES
# =========================

@never_cache
def mis_datos_view(request):
    if not request.session.get("vecino_id"):
        return redirect("login")

    vecino = get_object_or_404(Vecino, id_vecino=request.session.get("vecino_id"))

    cargo_actual = HistCargo.objects.filter(
        id_vecino=vecino,
        fecha_cargo_fin_real__isnull=True
    ).select_related("id_cargo").first()

    if request.method == "POST":
        vecino.telefono = request.POST.get("telefono")

        if request.session.get("rol") == "Admin":
            firma = request.FILES.get("firma")

            if firma:
                extension = firma.name.split(".")[-1].lower()
                nombre_archivo = f"presidentes/firma_{vecino.id_vecino}.{extension}"
                archivo_bytes = firma.read()

                supabase_storage.storage.from_("firmas").upload(
                    path=nombre_archivo,
                    file=archivo_bytes,
                    file_options={
                        "content-type": firma.content_type,
                        "upsert": "true"
                    }
                )

                firma_url = supabase_storage.storage.from_("firmas").get_public_url(nombre_archivo)
                vecino.firma_digital = firma_url

        vecino.save()
        messages.success(request, "Datos actualizados correctamente.")
        return redirect("mis_datos")

    return render(request, "mis_datos.html", {
        "vecino": vecino,
        "cargo_actual": cargo_actual
    })

@never_cache
def vecinos_mi_junta_view(request):
    if not request.session.get("vecino_id"):
        return redirect("login")

    if request.session.get("rol") not in ["Usuario", "Admin"]:
        messages.error(request, "No tienes permiso para ver esta sección.")
        return redirect("login")

    vecino_actual = get_object_or_404(
        Vecino,
        id_vecino=request.session.get("vecino_id")
    )

    residencia_activa = HistVivienda.objects.filter(
        id_vecino=vecino_actual,
        fecha_ter__isnull=True
    ).select_related("id_vivienda__id_junta").first()

    if not residencia_activa:
        messages.error(request, "Debe pertenecer a una junta para ver los vecinos.")
        if request.session.get("rol") == "Admin":
            return redirect("panel_presidente")
        return redirect("panel_vecino")

    junta = residencia_activa.id_vivienda.id_junta

    registros = HistVivienda.objects.filter(
        id_vivienda__id_junta=junta,
        fecha_ter__isnull=True
    ).select_related("id_vecino", "id_vivienda")

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
            "cargo": cargo_actual.id_cargo.nombre_cargo if cargo_actual else "Vecino",
            "condiciones": condiciones
        })

    return render(request, "vecinos_junta.html", {
        "junta": junta,
        "vecinos_data": vecinos_data,
        "rol": request.session.get("rol")
    })

@never_cache
def generar_certificado_view(request):

    if not request.session.get("vecino_id"):
        return redirect("login")

    if request.session.get("rol") not in ["Usuario", "Admin"]:
        messages.error(request, "No tienes permiso para generar certificados.")
        return redirect("login")   

    vecino = get_object_or_404(Vecino, id_vecino=request.session.get("vecino_id"))

    residencia = HistVivienda.objects.filter(
        id_vecino=vecino,
        fecha_ter__isnull=True
    ).select_related(
        "id_vivienda__id_junta",
        "id_vivienda__id_junta__id_comuna",
        "id_vivienda__id_junta__id_comuna__id_region"
    ).first()

    if not residencia:
        messages.error(request, "Debe pertenecer a una junta para generar el certificado.")
        return redirect("panel_vecino")

    junta = residencia.id_vivienda.id_junta
    vivienda = residencia.id_vivienda
    comuna = junta.id_comuna.nom_comuna

    presidente_cargo = HistCargo.objects.filter(
        id_directiva__id_junta=junta,
        id_cargo__nombre_cargo__iexact="Presidente",
        fecha_cargo_fin_real__isnull=True
    ).select_related("id_vecino").first()

    if not presidente_cargo:
        messages.error(request, "La junta aún no tiene presidente asignado.")
        return redirect("panel_vecino")

    presidente = presidente_cargo.id_vecino

    if not presidente.firma_digital:
        messages.error(request, "El presidente aún no ha subido su firma digital.")
        return redirect("panel_vecino")

    hoy = timezone.localtime(timezone.now()).date()
    anio = hoy.year

    certificado = CertificadoDeResidencia.objects.filter(
        id_vecino=vecino,
        id_vecino2=presidente,
        fecha_emision__date=hoy
    ).first()

    if certificado:
        numero_certificado = certificado.numero_certificado
    else:
        correlativo = CertificadoDeResidencia.objects.filter(
            fecha_emision__year=anio
        ).count() + 1

        numero_certificado = f"CERT-{anio}-{correlativo:04d}"

        certificado = CertificadoDeResidencia.objects.create(
            id_certificado=uuid.uuid4(),
            numero_certificado=numero_certificado,
            fecha_emision=timezone.now(),
            id_vecino=vecino,
            id_vecino2=presidente
        )

    carpeta_certificados = os.path.join(settings.MEDIA_ROOT, "certificados")
    os.makedirs(carpeta_certificados, exist_ok=True)

    nombre_pdf = f"{numero_certificado}_{vecino.id_vecino}.pdf"
    ruta_pdf = os.path.join(carpeta_certificados, nombre_pdf)

    meses = {
        1: "enero", 2: "febrero", 3: "marzo", 4: "abril",
        5: "mayo", 6: "junio", 7: "julio", 8: "agosto",
        9: "septiembre", 10: "octubre", 11: "noviembre", 12: "diciembre",
    }

    fecha_formal = f"{comuna}, {hoy.day} de {meses[hoy.month]} de {hoy.year}"

    direccion = f"{vivienda.nombre_calle} N° {vivienda.numero_calle}"

    if vivienda.tipo_vivienda == "D":
        direccion += f", Block {vivienda.num_block}, Departamento {vivienda.num_dpto}"

    direccion += f", comuna de {comuna}"

    c = canvas.Canvas(ruta_pdf, pagesize=letter)
    width, height = letter

    x_left = 80
    y = height - 60

    c.setFont("Helvetica", 9)
    c.drawRightString(width - 70, y, numero_certificado)

    y -= 35
    c.setFont("Helvetica-Bold", 13)
    c.drawCentredString(width / 2, y, "JUNTA DE VECINOS")
    y -= 18
    c.setFont("Helvetica-Bold", 14)
    c.drawCentredString(width / 2, y, f"“{junta.nombre.upper()}”")
    y -= 18
    c.setFont("Helvetica", 11)
    c.drawCentredString(width / 2, y, "UrbanLink")

    y -= 65
    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(width / 2, y, "CERTIFICADO DE RESIDENCIA")
    c.line(width / 2 - 125, y - 5, width / 2 + 125, y - 5)

    y -= 50
    c.setFont("Helvetica", 11)
    c.drawRightString(width - 80, y, fecha_formal)

    y -= 55
    c.setFont("Helvetica", 12)

    lineas = [
        f"Quien suscribe, Presidente de la Junta de Vecinos “{junta.nombre}”,",
        "certifica mediante el presente documento que:",
        "",
        f"Don(a): {vecino.pri_nombre} {vecino.apell_paterno} {vecino.apell_materno}",
        f"RUT N°: {vecino.rut}",
        f"Registra domicilio en: {direccion}.",
        "",
        "El presente certificado se extiende a petición del interesado(a),",
        "para los fines que estime pertinente.",
    ]

    for linea in lineas:
        if linea == "":
            y -= 15
        else:
            c.drawString(x_left, y, linea)
            y -= 25

    y -= 90

    try:
        respuesta = requests.get(presidente.firma_digital, timeout=10)

        if respuesta.status_code == 200:
            firma_img = ImageReader(BytesIO(respuesta.content))
            c.drawImage(
                firma_img,
                width / 2 - 90,
                y,
                width=180,
                height=70,
                preserveAspectRatio=True,
                mask="auto"
            )
    except Exception:
        pass

    y -= 25
    c.line(width / 2 - 120, y, width / 2 + 120, y)

    y -= 18
    c.setFont("Helvetica-Bold", 11)
    c.drawCentredString(
        width / 2,
        y,
        f"{presidente.pri_nombre.upper()} {presidente.apell_paterno.upper()} {presidente.apell_materno.upper()}"
    )

    y -= 16
    c.setFont("Helvetica", 10)
    c.drawCentredString(width / 2, y, f"PRESIDENTE JJ.VV. “{junta.nombre.upper()}”")

    c.setFont("Helvetica", 9)
    c.drawCentredString(width / 2, 50, "Documento emitido digitalmente a través de UrbanLink.")

    c.save()

    return FileResponse(
        open(ruta_pdf, "rb"),
        as_attachment=True,
        filename=f"{numero_certificado}_certificado_residencia.pdf"
    )
    
# =========================
# VISTAS VECINO
# =========================

@never_cache
def panel_vecino_view(request):
    if not request.session.get("vecino_id"):
        return redirect("login")

    if request.session.get("rol") != "Usuario":
        messages.error(request, "No tienes permiso para entrar a esa sección.")
        return redirect("login")

    vecino = get_object_or_404(Vecino, id_vecino=request.session.get("vecino_id"))

    residencia_activa = HistVivienda.objects.filter(
        id_vecino=vecino,
        fecha_ter__isnull=True
    ).select_related("id_vivienda__id_junta").first()

    return render(request, "panel_vecino.html", {
        "vecino": vecino,
        "residencia_activa": residencia_activa
    })

@never_cache
def mis_solicitudes_view(request):
    if not request.session.get("vecino_id"):
        return redirect("login")

    vecino = get_object_or_404(Vecino, id_vecino=request.session.get("vecino_id"))

    residencia_activa = HistVivienda.objects.filter(
        id_vecino=vecino,
        fecha_ter__isnull=True
    ).first()

    if not residencia_activa:
        messages.error(request, "Debe unirse a una junta para poder usar las solicitudes.")
        return redirect("panel_vecino")

    solicitudes = Solicitud.objects.filter(
        id_vecino=vecino
    ).select_related("id_tsolicitud").order_by("-fecha_solicitud")

    solicitudes_data = []

    for solicitud in solicitudes:
        hist_cierre = HistEstSol.objects.filter(
            id_solicitud=solicitud,
            id_est__nomb_est_sol__in=["APROBADO", "RECHAZADO"]
        ).order_by("-fecha_cb_estado").first()

        solicitudes_data.append({
            "solicitud": solicitud,
            "fecha_resuelta": hist_cierre.fecha_cb_estado if hist_cierre else None
        })

    return render(request, "vecino/mis_solicitudes.html", {
        "solicitudes_data": solicitudes_data
    })

@never_cache
def crear_solicitud_view(request):
    if not request.session.get("vecino_id"):
        return redirect("login")

    vecino = get_object_or_404(Vecino, id_vecino=request.session.get("vecino_id"))

    residencia_activa = HistVivienda.objects.filter(
        id_vecino=vecino,
        fecha_ter__isnull=True
    ).first()

    if not residencia_activa:
        messages.error(request, "Debe unirse a una junta para poder crear solicitudes.")
        return redirect("panel_vecino")

    tipos = Tiposolicitud.objects.all()

    if request.method == "POST":
        tipo = get_object_or_404(
            Tiposolicitud,
            id_tsolicitud=request.POST.get("id_tsolicitud")
        )

        solicitud = Solicitud.objects.create(
            id_solicitud=uuid.uuid4(),
            fecha_solicitud=timezone.now(),
            estado="EN PROCESO",
            descripcion = limpiar_texto(request.POST.get("descripcion")),
            comentario_presidente=None,
            id_vecino=vecino,
            id_tsolicitud=tipo
        )

        estado_en_proceso = EstadoSolicitud.objects.get(nomb_est_sol="EN PROCESO")

        HistEstSol.objects.create(
            id_solicitud=solicitud,
            id_est=estado_en_proceso,
            fecha_cb_estado=timezone.now()
        )

        messages.success(request, "Solicitud creada correctamente.")
        return redirect("mis_solicitudes")

    return render(request, "vecino/crear_solicitud.html", {
        "tipos": tipos
    })


# =========================
# VISTAS PRESIDENTE
# =========================

@never_cache
def panel_presidente_view(request):
    if not request.session.get("vecino_id"):
        return redirect("login")

    if request.session.get("rol") != "Admin":
        messages.error(request, "No tienes permiso para entrar a esa sección.")
        return redirect("login")

    return render(request, "panel_presidente.html")

@never_cache
def solicitudes_presidente_view(request):
    if not request.session.get("vecino_id"):
        return redirect("login")

    if request.session.get("rol") != "Admin":
        messages.error(request, "No tienes permiso para acceder a solicitudes.")
        return redirect("login")

    presidente = get_object_or_404(Vecino, id_vecino=request.session.get("vecino_id"))

    residencia_presidente = HistVivienda.objects.filter(
        id_vecino=presidente,
        fecha_ter__isnull=True
    ).select_related("id_vivienda__id_junta").first()

    if not residencia_presidente:
        messages.error(request, "No perteneces a ninguna junta.")
        return redirect("panel_presidente")

    junta = residencia_presidente.id_vivienda.id_junta

    filtro_estado = request.GET.get("estado", "Todas")
    busqueda = request.GET.get("q", "")
    
    registros_vecinos = HistVivienda.objects.filter(
        id_vivienda__id_junta=junta,
        fecha_ter__isnull=True
    ).select_related("id_vecino")

    vecinos_junta = [registro.id_vecino for registro in registros_vecinos]

    ids_vecinos_junta = [vecino.id_vecino for vecino in vecinos_junta]

    solicitudes = Solicitud.objects.filter(
        id_vecino__id_vecino__in=ids_vecinos_junta
    ).select_related("id_vecino", "id_tsolicitud").order_by("-fecha_solicitud")

    if filtro_estado != "Todas":
        solicitudes = solicitudes.filter(estado=filtro_estado)

    if busqueda:
        solicitudes = solicitudes.filter(
            models.Q(id_vecino__pri_nombre__icontains=busqueda) |
            models.Q(id_vecino__seg_nombre__icontains=busqueda) |
            models.Q(id_vecino__apell_paterno__icontains=busqueda) |
            models.Q(id_vecino__apell_materno__icontains=busqueda) |
            models.Q(id_vecino__rut__icontains=busqueda)
        )

    solicitudes_data = []

    for solicitud in solicitudes:
        hist_cierre = HistEstSol.objects.filter(
            id_solicitud=solicitud,
            id_est__nomb_est_sol__in=["APROBADO", "RECHAZADO"]
        ).order_by("-fecha_cb_estado").first()

        solicitudes_data.append({
            "solicitud": solicitud,
            "fecha_resuelta": hist_cierre.fecha_cb_estado if hist_cierre else None
        })

    return render(request, "presidente/solicitudes.html", {
        "junta": junta,
        "solicitudes_data": solicitudes_data,
        "filtro_estado": filtro_estado,
        "busqueda": busqueda,
    })

@never_cache
def cerrar_solicitud_view(request, id_solicitud):
    if not request.session.get("vecino_id"):
        return redirect("login")

    if request.session.get("rol") != "Admin":
        messages.error(request, "No tienes permiso para cerrar solicitudes.")
        return redirect("login")

    solicitud = get_object_or_404(Solicitud, id_solicitud=id_solicitud)

    if solicitud.estado != "EN PROCESO":
        messages.error(request, "Esta solicitud ya fue cerrada.")
        return redirect("solicitudes_presidente")

    if request.method == "POST":
        accion = request.POST.get("accion")
        comentario_presidente = request.POST.get("comentario_presidente")

        if accion == "aprobar":
            nuevo_estado = "APROBADO"
        elif accion == "rechazar":
            nuevo_estado = "RECHAZADO"
        else:
            messages.error(request, "Acción no válida.")
            return redirect("solicitudes_presidente")

        solicitud.estado = nuevo_estado
        solicitud.comentario_presidente = comentario_presidente
        solicitud.save()

        estado_obj = EstadoSolicitud.objects.get(nomb_est_sol=nuevo_estado)

        HistEstSol.objects.create(
            id_solicitud=solicitud,
            id_est=estado_obj,
            fecha_cb_estado=timezone.now()
        )

        messages.success(request, "Solicitud cerrada correctamente.")
        return redirect("solicitudes_presidente")

    return render(request, "presidente/cerrar_solicitud.html", {
        "solicitud": solicitud
    })
    

@never_cache
def certificados_presidente_view(request):
    if not request.session.get("vecino_id"):
        return redirect("login")

    if request.session.get("rol") != "Admin":
        messages.error(request, "No tienes permiso para ver certificados.")
        return redirect("login")

    presidente = get_object_or_404(Vecino, id_vecino=request.session.get("vecino_id"))

    busqueda = request.GET.get("q", "")

    certificados = CertificadoDeResidencia.objects.filter(
        id_vecino2=presidente
    ).select_related("id_vecino").order_by("-fecha_emision")

    if busqueda:
        certificados = certificados.filter(
            models.Q(id_vecino__pri_nombre__icontains=busqueda) |
            models.Q(id_vecino__seg_nombre__icontains=busqueda) |
            models.Q(id_vecino__apell_paterno__icontains=busqueda) |
            models.Q(id_vecino__apell_materno__icontains=busqueda) |
            models.Q(id_vecino__rut__icontains=busqueda)
        )

    return render(request, "presidente/certificados.html", {
        "certificados": certificados,
        "busqueda": busqueda,
    })

# =========================
# SUPERADMIN - GENERAL
# =========================

def es_superadmin(request):
    return request.session.get("rol") == "Superadmin"

@never_cache
def panel_superadmin_view(request):
    if not request.session.get("vecino_id"):
        return redirect("login")

    if not es_superadmin(request):
        messages.error(request, "No tienes permiso para entrar al panel Superadmin.")
        return redirect("login")

    total_juntas = Juntavecinos.objects.count()
    total_vecinos = Vecino.objects.count()

    return render(request, "panel_superadmin.html", {
        "total_juntas": total_juntas,
        "total_vecinos": total_vecinos,
    })


# =========================
# SUPERADMIN - GESTIÓN DE JUNTAS
# =========================

@never_cache
def listar_juntas_view(request):
    if not es_superadmin(request):
        return redirect("login")

    juntas = Juntavecinos.objects.all()

    return render(request, "superadmin/juntas/listar.html", {
        "juntas": juntas
    })

@never_cache
def crear_junta_view(request):
    if not es_superadmin(request):
        return redirect("login")

    regiones = Region.objects.all().order_by("nom_region")
    comunas = Comuna.objects.select_related("id_region").all().order_by("nom_comuna")

    if request.method == "POST":
        nombre = limpiar_mayusculas(request.POST.get("nombre"))
        direccion = limpiar_titulo(request.POST.get("direccion"))
        id_comuna = request.POST.get("id_comuna")

        comuna = get_object_or_404(Comuna, id_comuna=id_comuna)

        Juntavecinos.objects.create(
            id_junta=uuid.uuid4(),
            nombre=nombre,
            direccion=direccion,
            fecha_creacion=timezone.now(),
            id_comuna=comuna
        )

        messages.success(request, "Junta creada correctamente.")
        return redirect("listar_juntas")

    return render(request, "superadmin/juntas/crear.html", {
        "regiones": regiones,
        "comunas": comunas
    })

@never_cache
def editar_junta_view(request, id_junta):
    if not es_superadmin(request):
        return redirect("login")

    junta = get_object_or_404(Juntavecinos, id_junta=id_junta)
    regiones = Region.objects.all().order_by("nom_region")
    comunas = Comuna.objects.select_related("id_region").all().order_by("nom_comuna")

    if request.method == "POST":
        junta.nombre = request.POST.get("nombre")
        junta.direccion = limpiar_titulo(request.POST.get("direccion"))

        id_comuna = request.POST.get("id_comuna")
        junta.id_comuna = get_object_or_404(Comuna, id_comuna=id_comuna)

        junta.save()

        messages.success(request, "Junta actualizada correctamente.")
        return redirect("listar_juntas")

    return render(request, "superadmin/juntas/editar.html", {
        "junta": junta,
        "regiones": regiones,
        "comunas": comunas
    })

@never_cache
def eliminar_junta_view(request, id_junta):
    if not es_superadmin(request):
        return redirect("login")

    junta = get_object_or_404(Juntavecinos, id_junta=id_junta)

    tiene_vecinos = HistVivienda.objects.filter(
        id_vivienda__id_junta=junta
    ).exists()

    tiene_directivas = Directiva.objects.filter(
        id_junta=junta
    ).exists()

    if request.method == "POST":
        if tiene_vecinos or tiene_directivas:
            messages.error(
                request,
                "No se puede eliminar esta junta porque tiene vecinos o directivas asociadas. Primero debes quitar sus vecinos y registros asociados, o desactivarla."
            )
            return redirect("listar_juntas")

        junta.delete()
        messages.success(request, "Junta eliminada correctamente.")
        return redirect("listar_juntas")

    return render(request, "superadmin/juntas/eliminar.html", {
        "junta": junta,
        "tiene_vecinos": tiene_vecinos,
        "tiene_directivas": tiene_directivas,
    })

# =========================
# SUPERADMIN - VECINOS EN JUNTA
# =========================
@never_cache
def vecinos_junta_view(request, id_junta):
    if request.session.get("rol") != "Superadmin":
        return redirect("login")

    junta = get_object_or_404(Juntavecinos, id_junta=id_junta)

    registros = HistVivienda.objects.filter(
        id_vivienda__id_junta=junta,
        fecha_ter__isnull=True
    ).select_related("id_vecino", "id_vivienda")

    vecinos_data = []

    for registro in registros:
        cargo_actual = HistCargo.objects.filter(
            id_vecino=registro.id_vecino,
            fecha_cargo_fin_real__isnull=True
        ).select_related("id_cargo").first()

        vecinos_data.append({
            "registro": registro,
            "cargo_actual": cargo_actual.id_cargo.nombre_cargo if cargo_actual else "Vecino",
        })

    return render(request, "superadmin/juntas/vecinos.html", {
        "junta": junta,
        "vecinos_data": vecinos_data
    })

@never_cache
def asignar_vecino_junta_view(request, id_junta):
    if request.session.get("rol") != "Superadmin":
        return redirect("login")

    junta = get_object_or_404(Juntavecinos, id_junta=id_junta)

    vecinos_con_junta = HistVivienda.objects.filter(
        fecha_ter__isnull=True
    ).values_list("id_vecino", flat=True)

    vecinos = Vecino.objects.filter(
        vigencia="S"
    ).exclude(
        id_vecino__in=vecinos_con_junta
    ).order_by("pri_nombre", "apell_paterno")

    if request.method == "POST":
        id_vecino = request.POST.get("id_vecino")
        tipo_vivienda = request.POST.get("tipo_vivienda")
        nombre_calle = limpiar_titulo(request.POST.get("nombre_calle"))
        numero_calle = request.POST.get("numero_calle")
        num_block = request.POST.get("num_block") or None
        num_dpto = request.POST.get("num_dpto") or None

        vecino = get_object_or_404(Vecino, id_vecino=id_vecino)
        
        residencia_activa = HistVivienda.objects.filter(
            id_vecino=vecino,
            fecha_ter__isnull=True
        ).select_related("id_vivienda__id_junta").first()

        if residencia_activa:
            messages.error(
                request,
                f"El vecino ya pertenece a la junta '{residencia_activa.id_vivienda.id_junta.nombre}'. Primero debe ser removido de esa junta."
            )
            return redirect("asignar_vecino_junta", id_junta=junta.id_junta)

        ya_existe = HistVivienda.objects.filter(
            id_vecino=vecino,
            id_vivienda__id_junta=junta,
            fecha_ter__isnull=True
        ).exists()

        if ya_existe:
            messages.error(request, "Este vecino ya pertenece actualmente a esta junta.")
            return redirect("asignar_vecino_junta", id_junta=junta.id_junta)

        if tipo_vivienda == "C":
            num_block = None
            num_dpto = None

        if tipo_vivienda == "D":
            if not num_block or not num_dpto:
                messages.error(request, "Para departamento debes ingresar número de block y departamento.")
                return redirect("asignar_vecino_junta", id_junta=junta.id_junta)

        vivienda = Vivienda.objects.create(
            id_vivienda=uuid.uuid4(),
            tipo_vivienda=tipo_vivienda,
            nombre_calle=nombre_calle,
            numero_calle=numero_calle,
            num_block=num_block,
            num_dpto=num_dpto,
            id_junta=junta
        )

        HistVivienda.objects.create(
            fecha_ini=timezone.now().date(),
            fecha_ter=None,
            id_vivienda=vivienda,
            id_vecino=vecino
        )

        messages.success(request, "Vecino asignado correctamente a la junta.")
        return redirect("vecinos_junta", id_junta=junta.id_junta)

    return render(request, "superadmin/juntas/asignar_vecino.html", {
        "junta": junta,
        "vecinos": vecinos
    })

@never_cache    
def quitar_vecino_junta_view(request, id_junta, id_vecino):
    if request.session.get("rol") != "Superadmin":
        return redirect("login")

    junta = get_object_or_404(Juntavecinos, id_junta=id_junta)
    vecino = get_object_or_404(Vecino, id_vecino=id_vecino)

    registro = get_object_or_404(
        HistVivienda,
        id_vecino=vecino,
        id_vivienda__id_junta=junta,
        fecha_ter__isnull=True
    )

    if request.method == "POST":
        registro.fecha_ter = timezone.now().date()
        registro.save()

        messages.success(request, "Vecino quitado de la junta correctamente.")
        return redirect("vecinos_junta", id_junta=junta.id_junta)

    return render(request, "superadmin/juntas/quitar_vecino.html", {
        "junta": junta,
        "vecino": vecino,
        "registro": registro
    })

# =========================
# SUPERADMIN - DIRECTIVA Y CARGOS
# =========================

@never_cache
def crear_directiva_view(request, id_junta):
    if request.session.get("rol") != "Superadmin":
        return redirect("login")

    junta = get_object_or_404(Juntavecinos, id_junta=id_junta)

    if request.method == "POST":
        fecha_inicio = request.POST.get("fecha_inicio")
        fecha_fin = request.POST.get("fecha_fin")

        Directiva.objects.create(
            id_directiva=uuid.uuid4(),
            fecha_inicio_direct=fecha_inicio,
            fecha_fin_direct=fecha_fin,
            id_junta=junta
        )

        messages.success(request, "Directiva creada correctamente.")
        return redirect("vecinos_junta", id_junta=junta.id_junta)

    return render(request, "superadmin/juntas/crear_directiva.html", {
        "junta": junta
    })

@never_cache
def asignar_cargo_junta_view(request, id_junta):
    if request.session.get("rol") != "Superadmin":
        return redirect("login")

    junta = get_object_or_404(Juntavecinos, id_junta=id_junta)

    directiva = Directiva.objects.filter(
        id_junta=junta
    ).order_by("-fecha_inicio_direct").first()

    if not directiva:
        messages.error(request, "Esta junta aún no tiene una directiva creada.")
        return redirect("crear_directiva", id_junta=junta.id_junta)

    registros = HistVivienda.objects.filter(
        id_vivienda__id_junta=junta,
        fecha_ter__isnull=True
    ).select_related("id_vecino", "id_vivienda")

    cargos = Cargo.objects.all()

    if request.method == "POST":
        asignados = 0
        errores = 0

        for registro in registros:
            vecino = registro.id_vecino
            id_cargo = request.POST.get(f"cargo_{vecino.id_vecino}")

            if not id_cargo:
                continue

            cargo = get_object_or_404(Cargo, id_cargo=id_cargo)

            ya_tiene_cargo = HistCargo.objects.filter(
                id_vecino=vecino,
                fecha_cargo_fin_real__isnull=True
            ).exists()

            if ya_tiene_cargo:
                errores += 1
                continue

            cargo_ocupado = HistCargo.objects.filter(
                id_directiva=directiva,
                id_cargo=cargo,
                fecha_cargo_fin_real__isnull=True
            ).exists()

            if cargo_ocupado:
                messages.error(
                    request,
                    f"El cargo {cargo.nombre_cargo} ya está ocupado."
                )
                errores += 1
                continue

            HistCargo.objects.create(
                id_hist_cargo=uuid.uuid4(),
                id_vecino=vecino,
                id_cargo=cargo,
                id_directiva=directiva,
                fecha_cargo_tentativa=timezone.now().date(),
                fecha_cargo_fin=None,
                fecha_cargo_fin_real=None
            )

            if cargo.nombre_cargo.lower() == "presidente":
                rol_admin = Rol.objects.get(nombre_rol="Admin")
                vecino.id_rol = rol_admin
                vecino.save()

            asignados += 1

        if asignados > 0:
            messages.success(
                request,
                f"Se asignaron {asignados} cargo(s) correctamente."
            )

        if errores > 0:
            messages.warning(
                request,
                f"{errores} cargo(s) no pudieron asignarse."
            )

        if asignados == 0 and errores == 0:
            messages.error(request, "No seleccionaste ningún cargo.")

        return redirect("asignar_cargo_junta", id_junta=junta.id_junta)

    vecinos_data = []

    for registro in registros:
        cargo_actual = HistCargo.objects.filter(
            id_vecino=registro.id_vecino,
            fecha_cargo_fin_real__isnull=True
        ).select_related("id_cargo").first()

        vecinos_data.append({
            "vecino": registro.id_vecino,
            "vivienda": registro.id_vivienda,
            "cargo_actual": cargo_actual,
        })

    return render(request, "superadmin/juntas/asignar_cargo.html", {
        "junta": junta,
        "directiva": directiva,
        "vecinos_data": vecinos_data,
        "cargos": cargos
    })

@never_cache    
def quitar_cargo_vecino_view(request, id_junta, id_vecino):
    if request.session.get("rol") != "Superadmin":
        return redirect("login")

    junta = get_object_or_404(Juntavecinos, id_junta=id_junta)
    vecino = get_object_or_404(Vecino, id_vecino=id_vecino)

    cargo_actual = get_object_or_404(
        HistCargo,
        id_vecino=vecino,
        fecha_cargo_fin_real__isnull=True
    )

    if request.method == "POST":
        nombre_cargo = cargo_actual.id_cargo.nombre_cargo.lower()

        cargo_actual.fecha_cargo_fin_real = timezone.now().date()
        cargo_actual.save()

        if nombre_cargo == "presidente":
            rol_usuario = Rol.objects.get(nombre_rol="Usuario")
            vecino.id_rol = rol_usuario
            vecino.save()

        messages.success(request, "Cargo retirado correctamente.")
        return redirect("asignar_cargo_junta", id_junta=junta.id_junta)

    return render(request, "superadmin/juntas/quitar_cargo.html", {
        "junta": junta,
        "vecino": vecino,
        "cargo_actual": cargo_actual
    })
    

# =========================
# SUPERADMIN - GESTIÓN DE VECINOS
# ========================= 

@never_cache
def gestionar_vecinos_view(request):
    if not es_superadmin(request):
        return redirect("login")

    busqueda = request.GET.get("q", "")
    filtro_junta = request.GET.get("junta", "Todas")

    vecinos = Vecino.objects.filter(vigencia="S").order_by("pri_nombre", "apell_paterno")
    juntas = Juntavecinos.objects.all().order_by("nombre")

    if busqueda:
        vecinos = vecinos.filter(
            models.Q(pri_nombre__icontains=busqueda) |
            models.Q(seg_nombre__icontains=busqueda) |
            models.Q(apell_paterno__icontains=busqueda) |
            models.Q(apell_materno__icontains=busqueda) |
            models.Q(rut__icontains=busqueda)
        )

    if filtro_junta != "Todas":
        vecinos_ids = HistVivienda.objects.filter(
            id_vivienda__id_junta__id_junta=filtro_junta,
            fecha_ter__isnull=True
        ).values_list("id_vecino", flat=True)

        vecinos = vecinos.filter(id_vecino__in=vecinos_ids)

    vecinos_data = []

    for vecino in vecinos:
        residencia = HistVivienda.objects.filter(
            id_vecino=vecino,
            fecha_ter__isnull=True
        ).select_related("id_vivienda__id_junta").first()

        cargo_actual = HistCargo.objects.filter(
            id_vecino=vecino,
            fecha_cargo_fin_real__isnull=True
        ).select_related("id_cargo").first()

        condiciones = VecinoDiscap.objects.filter(
            id_vecino=vecino
        ).select_related("id_tipo_discap")

        vecinos_data.append({
            "vecino": vecino,
            "junta": residencia.id_vivienda.id_junta.nombre if residencia else "Sin junta",
            "cargo": cargo_actual.id_cargo.nombre_cargo if cargo_actual else "Vecino",
            "condiciones": condiciones,
        })

    return render(request, "superadmin/vecinos/gestionar.html", {
        "vecinos_data": vecinos_data,
        "juntas": juntas,
        "busqueda": busqueda,
        "filtro_junta": filtro_junta,
    })
    
@never_cache
def editar_vecino_superadmin_view(request, id_vecino):
    if not es_superadmin(request):
        return redirect("login")

    vecino = get_object_or_404(Vecino, id_vecino=id_vecino)
    tipos = TipoDiscapacidad.objects.all()

    condiciones_actuales = VecinoDiscap.objects.filter(id_vecino=vecino)
    ids_actuales = [
        str(item.id_tipo_discap.id_tipo_discap)
        for item in condiciones_actuales
    ]

    if request.method == "POST":
        vecino.pri_nombre = limpiar_mayusculas(request.POST.get("pri_nombre"))
        vecino.seg_nombre = limpiar_mayusculas(request.POST.get("seg_nombre")) or None
        vecino.apell_paterno = limpiar_mayusculas(request.POST.get("apell_paterno"))
        vecino.apell_materno = limpiar_mayusculas(request.POST.get("apell_materno"))
        vecino.telefono = request.POST.get("telefono")
        vecino.vigencia = request.POST.get("vigencia")
        vecino.save()

        seleccionadas = request.POST.getlist("discapacidades")

        VecinoDiscap.objects.filter(id_vecino=vecino).delete()

        for id_tipo in seleccionadas:
            tipo = get_object_or_404(TipoDiscapacidad, id_tipo_discap=id_tipo)

            VecinoDiscap.objects.create(
                id_tipo_discap=tipo,
                id_vecino=vecino,
                fecha_registro_discap=timezone.now().date()
            )

        messages.success(request, "Vecino actualizado correctamente.")
        return redirect("gestionar_vecinos")

    return render(request, "superadmin/vecinos/editar.html", {
        "vecino": vecino,
        "tipos": tipos,
        "ids_actuales": ids_actuales,
    })