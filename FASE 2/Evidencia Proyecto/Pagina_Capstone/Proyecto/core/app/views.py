import uuid

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone

from .models import *
from .supabase_client import supabase


# Views para usuarios
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

#
def panel_vecino_view(request):
    if not request.session.get("vecino_id"):
        return redirect("login")

    if request.session.get("rol") != "Usuario":
        messages.error(request, "No tienes permiso para entrar a esa sección.")
        return redirect("login")

    return render(request, "panel_vecino.html")


def panel_presidente_view(request):
    if not request.session.get("vecino_id"):
        return redirect("login")

    if request.session.get("rol") != "Admin":
        messages.error(request, "No tienes permiso para entrar a esa sección.")
        return redirect("login")

    return render(request, "panel_presidente.html")

#Views del SUPERADIN
def panel_superadmin_view(request):
    if not request.session.get("vecino_id"):
        return redirect("login")

    if request.session.get("rol") != "Superadmin":
        messages.error(request, "No tienes permiso para entrar a esa sección.")
        return redirect("login")

    return render(request, "panel_superadmin.html")


def es_superadmin(request):
    return request.session.get("rol") == "Superadmin"


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