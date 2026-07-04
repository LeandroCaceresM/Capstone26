import uuid

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.db import models

from app.constants import CARGO_PRESIDENTE, ROL_ADMIN, ROL_SUPERADMIN, ROL_USUARIO, VIGENCIA_ACTIVA
from app.models import *
from app.utils import *
from app.validators import *
from app.decorators import role_required

# =========================
# SUPERADMIN - GENERAL
# =========================

@never_cache
@role_required(ROL_SUPERADMIN)
def panel_superadmin_view(request):
    total_juntas = Juntavecinos.objects.count()

    total_vecinos = Vecino.objects.count()

    usuarios_activos = Vecino.objects.filter(
        vigencia="S"
    ).count()

    total_presidentes = Vecino.objects.filter(
        id_rol__nombre_rol=ROL_ADMIN
    ).count()

    ultimas_juntas = (
        Juntavecinos.objects
        .select_related("id_sector__id_comuna__id_region")
        .order_by("-fecha_creacion")[:5]
    )

    vecinos_recientes = Vecino.objects.all().order_by("-fecha_registro")[:5]

    return render(request, "panel_superadmin.html", {
        "total_juntas": total_juntas,
        "total_vecinos": total_vecinos,
        "usuarios_activos": usuarios_activos,
        "total_presidentes": total_presidentes,
        "ultimas_juntas": ultimas_juntas,
        "vecinos_recientes": vecinos_recientes,
    })


@never_cache
@role_required(ROL_SUPERADMIN)
def listar_sectores_view(request):
    busqueda = request.GET.get("q", "")

    sectores = Sector.objects.select_related(
        "id_comuna",
        "id_comuna__id_region"
    ).order_by(
        "id_comuna__id_region__nom_region",
        "id_comuna__nom_comuna",
        "nombre_sector"
    )

    if busqueda:
        sectores = sectores.filter(
            models.Q(nombre_sector__icontains=busqueda) |
            models.Q(id_comuna__nom_comuna__icontains=busqueda) |
            models.Q(id_comuna__id_region__nom_region__icontains=busqueda)
        )

    return render(request, "superadmin/sectores/listar.html", {
        "sectores": sectores,
        "busqueda": busqueda,
    })

# =========================
# SUPERADMIN - GESTIÓN DE SECTORES
# =========================

@never_cache
@role_required(ROL_SUPERADMIN)
def crear_sector_view(request):
    regiones = Region.objects.all().order_by("nom_region")

    comunas = Comuna.objects.select_related(
        "id_region"
    ).order_by(
        "id_region__nom_region",
        "nom_comuna"
    )

    if request.method == "POST":
        nombre_sector = limpiar_mayusculas(request.POST.get("nombre_sector"))
        id_comuna = request.POST.get("id_comuna")

        comuna = get_object_or_404(Comuna, id_comuna=id_comuna)

        if Sector.objects.filter(
            nombre_sector=nombre_sector,
            id_comuna=comuna
        ).exists():
            messages.error(request, "Este sector ya existe en la comuna seleccionada.")
            return redirect("crear_sector")

        Sector.objects.create(
            id_sector=uuid.uuid4(),
            nombre_sector=nombre_sector,
            id_comuna=comuna
        )

        messages.success(request, "Sector creado correctamente.")
        return redirect("listar_sectores")

    return render(request, "superadmin/sectores/crear.html", {
        "regiones": regiones,
        "comunas": comunas,
    })

# =========================
# SUPERADMIN - GESTIÓN DE JUNTAS
# =========================

@never_cache
@role_required(ROL_SUPERADMIN)
def listar_juntas_view(request):
    juntas = Juntavecinos.objects.select_related(
        "id_sector__id_comuna__id_region"
    ).order_by("nombre")

    return render(request, "superadmin/juntas/listar.html", {
        "juntas": juntas
    })

@never_cache
@role_required(ROL_SUPERADMIN)
def crear_junta_view(request):
    regiones = Region.objects.all().order_by("nom_region")

    comunas = Comuna.objects.select_related(
        "id_region"
    ).all().order_by("nom_comuna")

    sectores = Sector.objects.select_related(
        "id_comuna__id_region"
    ).all().order_by(
        "id_comuna__id_region__nom_region",
        "id_comuna__nom_comuna",
        "nombre_sector"
    )

    if request.method == "POST":
        nombre = limpiar_titulo(request.POST.get("nombre"))
        direccion = limpiar_titulo(request.POST.get("direccion"))

        sector = get_object_or_404(
            Sector,
            id_sector=request.POST.get("id_sector")
        )

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
        "regiones": regiones,
        "comunas": comunas,
        "sectores": sectores,
    })

@never_cache
@role_required(ROL_SUPERADMIN)
def editar_junta_view(request, id_junta):
    junta = get_object_or_404(Juntavecinos, id_junta=id_junta)

    regiones = Region.objects.all().order_by("nom_region")

    comunas = Comuna.objects.select_related(
        "id_region"
    ).all().order_by("nom_comuna")

    sectores = Sector.objects.select_related(
        "id_comuna__id_region"
    ).all().order_by(
        "id_comuna__id_region__nom_region",
        "id_comuna__nom_comuna",
        "nombre_sector"
    )

    if request.method == "POST":
        junta.nombre = limpiar_titulo(request.POST.get("nombre"))
        junta.direccion = limpiar_titulo(request.POST.get("direccion"))

        sector = get_object_or_404(
            Sector,
            id_sector=request.POST.get("id_sector")
        )

        junta.id_sector = sector
        junta.save()

        messages.success(request, "Junta actualizada correctamente.")
        return redirect("listar_juntas")

    return render(request, "superadmin/juntas/editar.html", {
        "junta": junta,
        "regiones": regiones,
        "comunas": comunas,
        "sectores": sectores,
    })

@never_cache
@role_required(ROL_SUPERADMIN)
def eliminar_junta_view(request, id_junta):

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
@role_required(ROL_SUPERADMIN)
def vecinos_junta_view(request, id_junta):

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
@role_required(ROL_SUPERADMIN)
def asignar_vecino_junta_view(request, id_junta):

    junta = get_object_or_404(Juntavecinos, id_junta=id_junta)

    vecinos_con_junta = HistVivienda.objects.filter(
        fecha_ter__isnull=True
    ).values_list("id_vecino", flat=True)

    vecinos = Vecino.objects.filter(
        vigencia=VIGENCIA_ACTIVA
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
@role_required(ROL_SUPERADMIN)    
def quitar_vecino_junta_view(request, id_junta, id_vecino):

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
@role_required(ROL_SUPERADMIN)
def crear_directiva_view(request, id_junta):
    
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
@role_required(ROL_SUPERADMIN)
def asignar_cargo_junta_view(request, id_junta):

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

            if cargo.nombre_cargo.lower() == CARGO_PRESIDENTE.lower():
                rol_admin = Rol.objects.get(nombre_rol=ROL_ADMIN)
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
@role_required(ROL_SUPERADMIN)    
def quitar_cargo_vecino_view(request, id_junta, id_vecino):

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

        if nombre_cargo == CARGO_PRESIDENTE:
            rol_usuario = Rol.objects.get(nombre_rol=ROL_USUARIO)
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
@role_required(ROL_SUPERADMIN)
def gestionar_vecinos_view(request):

    busqueda = request.GET.get("q", "")
    filtro_junta = request.GET.get("junta", "Todas")

    vecinos = Vecino.objects.filter(vigencia=VIGENCIA_ACTIVA).order_by("pri_nombre", "apell_paterno")
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
@role_required(ROL_SUPERADMIN)
def editar_vecino_superadmin_view(request, id_vecino):

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