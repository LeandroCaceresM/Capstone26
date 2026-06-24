import uuid
import os
import requests

from io import BytesIO

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.conf import settings
from django.http import FileResponse

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.utils import ImageReader

from .models import *
from .supabase_client import supabase
from .supabase_storage_client import supabase_storage


#VISTAS GENERALES 
def registro_view(request):
    if request.method == "POST":
        correo = request.POST.get("correo")
        password = request.POST.get("password")

        rut = request.POST.get("rut")
        pri_nombre = request.POST.get("pri_nombre")
        seg_nombre = request.POST.get("seg_nombre")
        apell_paterno = request.POST.get("apell_paterno")
        apell_materno = request.POST.get("apell_materno")
        telefono = request.POST.get("telefono")
        fecha_de_nacimiento = request.POST.get("fecha_de_nacimiento")

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
                seg_nombre=seg_nombre or None,
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

    return render(request, "registro.html")

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

def logout_view(request):
    request.session.flush()
    messages.success(request, "Sesión cerrada correctamente.")
    return redirect("login")

    #RECUPERAR / CAMBIAR CONTRASEÑA

def recuperar_contrasenia(request):
    return render(request, "recuperar_contrasenia.html")

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

@never_cache
def generar_certificado_view(request):
    if not request.session.get("vecino_id"):
        return redirect("login")

    vecino = get_object_or_404(Vecino, id_vecino=request.session.get("vecino_id"))

    residencia = HistVivienda.objects.filter(
        id_vecino=vecino,
        fecha_ter__isnull=True
    ).select_related("id_vivienda__id_junta").first()

    if not residencia:
        messages.error(request, "Debe pertenecer a una junta para generar el certificado.")
        return redirect("panel_vecino")

    junta = residencia.id_vivienda.id_junta
    vivienda = residencia.id_vivienda

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

    carpeta_certificados = os.path.join(settings.MEDIA_ROOT, "certificados")
    os.makedirs(carpeta_certificados, exist_ok=True)

    nombre_pdf = f"certificado_{vecino.id_vecino}.pdf"
    ruta_pdf = os.path.join(carpeta_certificados, nombre_pdf)

    c = canvas.Canvas(ruta_pdf, pagesize=letter)
    width, height = letter

    # Márgenes
    x_left = 80
    y = height - 70

    # Encabezado
    c.setFont("Helvetica-BoldOblique", 12)
    c.drawCentredString(width / 2, y, f"JUNTA DE VECINOS {junta.nombre.upper()}")
    y -= 20
    c.drawCentredString(width / 2, y, "URBANLINK")

    # Título
    y -= 70
    c.setFont("Helvetica-BoldOblique", 14)
    c.drawCentredString(width / 2, y, "CERTIFICADO DE RESIDENCIA")
    c.line(width / 2 - 105, y - 3, width / 2 + 105, y - 3)

    # Cuerpo
    y -= 60
    c.setFont("Helvetica-Oblique", 12)

    lineas = [
        f"Quien suscribe, presidente de la Junta de Vecinos {junta.nombre},",
        "certifica mediante el presente documento que:",
    ]

    for linea in lineas:
        c.drawString(x_left, y, linea)
        y -= 28

    # Datos vecino
    c.setFont("Helvetica-BoldOblique", 12)
    c.drawString(x_left, y, "Don(a):")
    c.setFont("Helvetica-Oblique", 12)
    c.drawString(x_left + 70, y, f"{vecino.pri_nombre} {vecino.apell_paterno} {vecino.apell_materno}")
    y -= 28

    c.setFont("Helvetica-BoldOblique", 12)
    c.drawString(x_left, y, "RUT Nº:")
    c.setFont("Helvetica-Oblique", 12)
    c.drawString(x_left + 70, y, str(vecino.rut))
    y -= 28

    direccion = f"{vivienda.nombre_calle} {vivienda.numero_calle}"
    if vivienda.num_block:
        direccion += f", Block {vivienda.num_block}"
    if vivienda.num_dpto:
        direccion += f", Dpto {vivienda.num_dpto}"

    c.drawString(x_left, y, f"Tiene su domicilio en {direccion},")
    y -= 28
    c.drawString(x_left, y, f"perteneciente a la junta de vecinos {junta.nombre}.")
    y -= 50

    # Texto final
    c.setFont("Helvetica-Oblique", 12)
    c.drawString(x_left, y, "Se extiende el presente certificado a petición del interesado(a),")
    y -= 25
    c.drawString(x_left, y, "para los fines que estime pertinente.")

    # Firma
    y -= 110
    if presidente.firma_digital:
        respuesta = requests.get(presidente.firma_digital)

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

    y -= 25
    c.setFont("Helvetica-BoldOblique", 11)
    c.drawCentredString(
        width / 2,
        y,
        f"PRESIDENTE JJ.VV. {junta.nombre.upper()}"
    )
    y -= 18
    c.drawCentredString(
        width / 2,
        y,
        f"{presidente.pri_nombre.upper()} {presidente.apell_paterno.upper()} {presidente.apell_materno.upper()}"
    )

    # Fecha inferior
    c.setFont("Helvetica-Oblique", 11)
    fecha_actual = timezone.localtime(timezone.now()).strftime("%d/%m/%Y")
    c.drawCentredString(width / 2, 70, f"Emitido con fecha {fecha_actual}")

    c.save()

    CertificadoDeResidencia.objects.create(
        id_certificado=uuid.uuid4(),
        fecha_emision=timezone.now(),
        id_vecino=vecino,
        id_vecino2=presidente
    )

    return FileResponse(open(ruta_pdf, "rb"), as_attachment=True, filename="certificado_residencia.pdf")

#VISTAS GENERALES (SERVICIOS)

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
        vecino.save()

        messages.success(request, "Teléfono actualizado correctamente.")
        return redirect("mis_datos")

    return render(request, "mis_datos.html", {
        "vecino": vecino,
        "cargo_actual": cargo_actual
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
        id_tsolicitud = request.POST.get("id_tsolicitud")
        descripcion = request.POST.get("descripcion")

        tipo = get_object_or_404(Tiposolicitud, id_tsolicitud=id_tsolicitud)

        solicitud = Solicitud.objects.create(
            id_solicitud=uuid.uuid4(),
            fecha_solicitud=timezone.now(),
            estado="EN PROCESO",
            comentario=descripcion,
            id_vecino=vecino,
            id_tsolicitud=tipo
        )

        estado_en_proceso = EstadoSolicitud.objects.get(nomb_est_sol="EN PROCESO")

        HistEstSol.objects.create(
            id_solicitud=solicitud,
            id_est=estado_en_proceso,
            fecha_cb_estado=timezone.now()
        )

        messages.success(request, "Solicitud enviada correctamente.")
        return redirect("mis_solicitudes")

    return render(request, "vecino/crear_solicitud.html", {
        "tipos": tipos
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

        vecinos_data.append({
            "vecino": registro.id_vecino,
            "cargo": cargo_actual.id_cargo.nombre_cargo if cargo_actual else "Vecino"
        })

    return render(request, "vecinos_junta.html", {
        "junta": junta,
        "vecinos_data": vecinos_data,
        "rol": request.session.get("rol")
    })


#VISTA DE VECINO (USUARIO)
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
            descripcion=request.POST.get("descripcion"),
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



#VISTA DEL PRESIDENTE (ADMIN)
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
    filtro_vecino = request.GET.get("vecino", "Todos")

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

    if filtro_vecino != "Todos":
        solicitudes = solicitudes.filter(id_vecino__id_vecino=filtro_vecino)

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
        "filtro_vecino": filtro_vecino,
        "vecinos_junta": vecinos_junta,
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
def subir_firma_view(request):
    if not request.session.get("vecino_id"):
        return redirect("login")

    if request.session.get("rol") != "Admin":
        messages.error(request, "No tienes permiso para subir firma.")
        return redirect("login")

    presidente = get_object_or_404(Vecino, id_vecino=request.session.get("vecino_id"))

    if request.method == "POST":
        firma = request.FILES.get("firma")

        if not firma:
            messages.error(request, "Debe seleccionar una imagen.")
            return redirect("subir_firma")

        extension = firma.name.split(".")[-1].lower()
        nombre_archivo = f"presidentes/firma_{presidente.id_vecino}.{extension}"

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

        presidente.firma_digital = firma_url
        presidente.save()

        messages.success(request, "Firma digital subida correctamente.")
        return redirect("panel_presidente")

    return render(request, "presidente/subir_firma.html", {
        "presidente": presidente
    })

#Views del SUPERADMIN
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

def listar_juntas_view(request):
    if not es_superadmin(request):
        return redirect("login")

    juntas = Juntavecinos.objects.all()

    return render(request, "superadmin/juntas/listar.html", {
        "juntas": juntas
    })

def crear_junta_view(request):
    if not es_superadmin(request):
        return redirect("login")

    sectores = Sector.objects.all()

    if request.method == "POST":
        nombre = request.POST.get("nombre")
        direccion = request.POST.get("direccion")
        id_sector = request.POST.get("id_sector")

        sector = get_object_or_404(Sector, id_sector=id_sector)

        Juntavecinos.objects.create(
            id_junta=uuid.uuid4(),
            nombre=nombre,
            direccion=direccion,
            fecha_creacion=timezone.now(),
            id_sector=sector
        )

        messages.success(request, "Junta creada correctamente.")
        return redirect("listar_juntas")

    return render(request, "superadmin/juntas/crear.html", {
        "sectores": sectores
    })

def editar_junta_view(request, id_junta):
    if not es_superadmin(request):
        return redirect("login")

    junta = get_object_or_404(Juntavecinos, id_junta=id_junta)
    sectores = Sector.objects.all()

    if request.method == "POST":
        junta.nombre = request.POST.get("nombre")
        junta.direccion = request.POST.get("direccion")

        id_sector = request.POST.get("id_sector")
        junta.id_sector = get_object_or_404(Sector, id_sector=id_sector)

        junta.save()

        messages.success(request, "Junta actualizada correctamente.")
        return redirect("listar_juntas")

    return render(request, "superadmin/juntas/editar.html", {
        "junta": junta,
        "sectores": sectores
    })

def eliminar_junta_view(request, id_junta):
    if not es_superadmin(request):
        return redirect("login")

    junta = get_object_or_404(Juntavecinos, id_junta=id_junta)

    if request.method == "POST":
        junta.delete()
        messages.success(request, "Junta eliminada correctamente.")
        return redirect("listar_juntas")

    return render(request, "superadmin/juntas/eliminar.html", {
        "junta": junta
    })

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

def asignar_vecino_junta_view(request, id_junta):
    if request.session.get("rol") != "Superadmin":
        return redirect("login")

    junta = get_object_or_404(Juntavecinos, id_junta=id_junta)

    vecinos = Vecino.objects.filter(vigencia="S")

    if request.method == "POST":
        id_vecino = request.POST.get("id_vecino")
        tipo_vivienda = request.POST.get("tipo_vivienda")
        nombre_calle = request.POST.get("nombre_calle")
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
      
def editar_vecino_junta_view(request, id_junta, id_vecino):
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

    vivienda = registro.id_vivienda

    if request.method == "POST":
        vecino.pri_nombre = request.POST.get("pri_nombre")
        vecino.seg_nombre = request.POST.get("seg_nombre") or None
        vecino.apell_paterno = request.POST.get("apell_paterno")
        vecino.apell_materno = request.POST.get("apell_materno")
        vecino.correo = request.POST.get("correo") or None
        vecino.telefono = request.POST.get("telefono")
        vecino.save()

        tipo_vivienda = request.POST.get("tipo_vivienda")
        num_block = request.POST.get("num_block") or None
        num_dpto = request.POST.get("num_dpto") or None

        if tipo_vivienda == "C":
            num_block = None
            num_dpto = None

        if tipo_vivienda == "D":
            if not num_block or not num_dpto:
                messages.error(request, "Para departamento debes ingresar número de block y departamento.")
                return redirect(
                    "editar_vecino_junta",
                    id_junta=junta.id_junta,
                    id_vecino=vecino.id_vecino
                )

        vivienda.tipo_vivienda = tipo_vivienda
        vivienda.nombre_calle = request.POST.get("nombre_calle")
        vivienda.numero_calle = request.POST.get("numero_calle")
        vivienda.num_block = num_block
        vivienda.num_dpto = num_dpto
        vivienda.save()

        messages.success(request, "Datos del vecino actualizados correctamente.")
        return redirect("vecinos_junta", id_junta=junta.id_junta)

    return render(request, "superadmin/juntas/editar_vecino.html", {
        "junta": junta,
        "vecino": vecino,
        "vivienda": vivienda
    })
    
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
        id_vecino = request.POST.get("id_vecino")
        id_cargo = request.POST.get("id_cargo")

        vecino = get_object_or_404(Vecino, id_vecino=id_vecino)
        cargo = get_object_or_404(Cargo, id_cargo=id_cargo)

        ya_tiene_cargo = HistCargo.objects.filter(
            id_vecino=vecino,
            fecha_cargo_fin_real__isnull=True
        ).exists()

        if ya_tiene_cargo:
            messages.error(request, "Este vecino ya tiene un cargo activo.")
            return redirect("asignar_cargo_junta", id_junta=junta.id_junta)

        cargo_ocupado = HistCargo.objects.filter(
            id_directiva=directiva,
            id_cargo=cargo,
            fecha_cargo_fin_real__isnull=True
        ).exists()

        if cargo_ocupado:
            messages.error(request, f"El cargo {cargo.nombre_cargo} ya está ocupado.")
            return redirect("asignar_cargo_junta", id_junta=junta.id_junta)

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

        messages.success(request, "Cargo asignado correctamente.")
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