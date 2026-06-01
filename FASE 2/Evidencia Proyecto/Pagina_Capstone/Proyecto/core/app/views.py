from django.http import HttpResponse
from django.shortcuts import render

#Imports del gpt
from django.shortcuts import render, redirect
from .models import Vecino, JuntaVecinos, Rol, Cargo
import uuid
from django.utils import timezone

#Views para usuarios
def tutin(request):
    return render(request, 'debug/tutin.html')

#Views para pruebas

#Crear un vecino desde un formulario, eliminar luego.
def prueba_vecino(request):
    if request.method == 'POST':
        Vecino.objects.create(
            id_vecino=uuid.uuid4(),
            rut=request.POST['rut'],
            pri_nombre=request.POST['pri_nombre'],
            seg_nombre=request.POST.get('seg_nombre'),
            apell_paterno=request.POST['apell_paterno'],
            apell_materno=request.POST['apell_materno'],
            correo=request.POST['correo'],
            telefono=request.POST['telefono'],
            direccion=request.POST['direccion'],
            fecha_registro=timezone.now(),
            juntavecinos_id_junta=JuntaVecinos.objects.get(
                id_junta=request.POST['junta']
            ),
            rol_id_rol=Rol.objects.get(
                id_rol=request.POST['rol']
            ),
            cargo_id_cargo=Cargo.objects.get(
                id_cargo=request.POST['cargo']
            ) if request.POST['cargo'] else None,
            vigencia=True
        )

        return render(request, 'debug/ok.html')

    context = {
        'juntas': JuntaVecinos.objects.all(),
        'roles': Rol.objects.all(),
        'cargos': Cargo.objects.all()
    }

    return render(request, 'debug/prueba_vecino.html', context)

from django.shortcuts import render
from django.utils import timezone
from .models import JuntaVecinos, Sector
import uuid

#View para crear una junta de vecinos, eliminar luego.
def crear_junta(request):
    if request.method == 'POST':
        JuntaVecinos.objects.create(
            id_junta=uuid.uuid4(),
            nombre=request.POST['nombre'],
            direccion=request.POST['direccion'],
            fecha_creacion=timezone.now(),
            sector_id_sector=Sector.objects.get(
                id_sector=request.POST['sector']
            )
        )

        return render(request, 'debug/junta_ok.html')

    return render(request, 'debug/crear_junta.html', {
        'sectores': Sector.objects.all()
    })
    
from django.shortcuts import render, get_object_or_404
from .models import Vecino

#View para mostrar la región de un vecino, eliminar luego.
def ver_region_vecino(request, id_vecino):

    vecino = get_object_or_404(
        Vecino.objects.select_related(
            'juntavecinos_id_junta__sector_id_sector__comuna_id_comuna__region_id_region'
        ),
        id_vecino=id_vecino
    )

    region = (
        vecino
        .juntavecinos_id_junta
        .sector_id_sector
        .comuna_id_comuna
        .region_id_region
    )

    context = {
        'vecino': vecino,
        'region': region
    }

    return render(request, 'ver_region.html', context)