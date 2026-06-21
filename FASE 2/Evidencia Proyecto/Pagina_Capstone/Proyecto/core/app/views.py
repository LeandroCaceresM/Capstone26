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


def asignar_cargo_view(request):
    if not es_superadmin(request):
        return redirect("login")

    vecinos = Vecino.objects.all()
    cargos = Cargo.objects.all()
    directivas = Directiva.objects.all()

    if request.method == "POST":
        id_vecino = request.POST.get("id_vecino")
        id_cargo = request.POST.get("id_cargo")
        id_directiva = request.POST.get("id_directiva")
        fecha_inicio = request.POST.get("fecha_inicio")
        fecha_fin = request.POST.get("fecha_fin")

        vecino = get_object_or_404(Vecino, id_vecino=id_vecino)
        cargo = get_object_or_404(Cargo, id_cargo=id_cargo)
        directiva = get_object_or_404(Directiva, id_directiva=id_directiva)

        HistCargo.objects.create(
            id_vecino=vecino,
            id_cargo=cargo,
            id_directiva=directiva,
            fecha_cargo_tentativa=fecha_inicio,
            fecha_cargo_fin=fecha_fin,
            fecha_cargo_fin_real=None
        )

        if cargo.nombre_cargo.lower() == "presidente":
            rol_admin = Rol.objects.get(nombre_rol="Admin")
            vecino.id_rol = rol_admin
            vecino.save()

        messages.success(request, "Cargo asignado correctamente.")
        return redirect("panel_superadmin")

    return render(request, "superadmin/asignar_cargo.html", {
        "vecinos": vecinos,
        "cargos": cargos,
        "directivas": directivas
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
            "cargo_actual": cargo_actual.id_cargo.nombre_cargo if cargo_actual else "Sin cargo",
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
        vivienda.tipo_vivienda = request.POST.get("tipo_vivienda")
        vivienda.nombre_calle = request.POST.get("nombre_calle")
        vivienda.numero_calle = request.POST.get("numero_calle")
        vivienda.num_block = request.POST.get("num_block") or None
        vivienda.num_dpto = request.POST.get("num_dpto") or None
        vivienda.save()

        messages.success(request, "Datos de vivienda actualizados correctamente.")
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