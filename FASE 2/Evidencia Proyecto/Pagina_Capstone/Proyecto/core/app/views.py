from django.shortcuts import render
from django.utils import timezone
import uuid

from .models import Vecino, Juntavecinos, Rol, Cargo, Sector, Region


# Views para usuarios
def tutin(request):
    return render(request, 'debug/tutin.html')


# Crear un vecino (ajustado al modelo nuevo)
def prueba_vecino(request):
    if request.method == 'POST':
        Vecino.objects.create(
            id_vecino=uuid.uuid4(),
            rut=request.POST['rut'],
            pri_nombre=request.POST['pri_nombre'],
            seg_nombre=request.POST.get('seg_nombre'),
            apell_paterno=request.POST['apell_paterno'],
            apell_materno=request.POST['apell_materno'],
            correo=request.POST.get('correo'),
            telefono=request.POST['telefono'],
            fecha_de_nacimiento=request.POST['fecha_de_nacimiento'],
            vigencia=request.POST.get('vigencia', 'S'),
            fecha_registro=timezone.now(),
            id_rol=Rol.objects.get(id_rol=request.POST['rol']),
        )

        return render(request, 'debug/ok.html')

    context = {
        'roles': Rol.objects.all(),
    }

    return render(request, 'debug/prueba_vecino.html', context)


# Crear junta de vecinos (ajustado a Juntavecinos)
def crear_junta(request):
    if request.method == 'POST':
        Juntavecinos.objects.create(
            id_junta=uuid.uuid4(),
            nombre=request.POST['nombre'],
            direccion=request.POST['direccion'],
            fecha_creacion=timezone.now(),
            id_sector=Sector.objects.get(
                id_sector=request.POST['sector']
            )
        )

        return render(request, 'debug/junta_ok.html')

    return render(request, 'debug/crear_junta.html', {
        'sectores': Sector.objects.all()
    })


# Vecinos filtrados por región (vía HistVivienda -> Vivienda -> Junta -> Sector -> Comuna -> Región)
def vecinos_por_region(request):
    regiones = Region.objects.all().order_by('nom_region')

    region_id = request.GET.get('region')
    vecinos = None
    region_seleccionada = None

    if region_id:
        vecinos = Vecino.objects.filter(
            histvivienda__id_vivienda__id_junta__id_sector__id_comuna__id_region__id_region=region_id
        ).distinct()

        region_seleccionada = Region.objects.get(id_region=region_id)

    context = {
        'regiones': regiones,
        'vecinos': vecinos,
        'region_seleccionada': region_seleccionada
    }

    return render(request, 'debug/vecinos_por_region.html', context)