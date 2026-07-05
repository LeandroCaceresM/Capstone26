from django.urls import path
from app import views

urlpatterns = [
    path("panel-superadmin/", views.panel_superadmin_view, name="panel_superadmin"),


    path(
        "superadmin/solicitudes/",
        views.solicitudes_superadmin_view,
        name="solicitudes_superadmin"
    ),
    path(
        "superadmin/solicitudes/<uuid:id_solicitud>/cerrar/",
        views.cerrar_solicitud_superadmin_view,
        name="cerrar_solicitud_superadmin"
    ),

    path("superadmin/sectores/", views.listar_sectores_view, name="listar_sectores"),
    path("superadmin/sectores/crear/", views.crear_sector_view, name="crear_sector"),
    
    path("superadmin/juntas/", views.listar_juntas_view, name="listar_juntas"),
    path("superadmin/juntas/crear/", views.crear_junta_view, name="crear_junta"),
    path("superadmin/juntas/editar/<uuid:id_junta>/", views.editar_junta_view, name="editar_junta"),
    path("superadmin/juntas/eliminar/<uuid:id_junta>/", views.eliminar_junta_view, name="eliminar_junta"),

    path("superadmin/juntas/<uuid:id_junta>/vecinos/", views.vecinos_junta_view, name="vecinos_junta"),
    path("superadmin/juntas/<uuid:id_junta>/vecinos/asignar/", views.asignar_vecino_junta_view, name="asignar_vecino_junta"),

    path(
        "superadmin/juntas/<uuid:id_junta>/vecinos/<uuid:id_vecino>/quitar/",
        views.quitar_vecino_junta_view,
        name="quitar_vecino_junta"
    ),

    path(
        "superadmin/juntas/<uuid:id_junta>/directiva/crear/",
        views.crear_directiva_view,
        name="crear_directiva"
    ),

    path(
        "superadmin/juntas/<uuid:id_junta>/cargos/asignar/",
        views.asignar_cargo_junta_view,
        name="asignar_cargo_junta"
    ),

    path(
        "superadmin/juntas/<uuid:id_junta>/vecinos/<uuid:id_vecino>/quitar-cargo/",
        views.quitar_cargo_vecino_view,
        name="quitar_cargo_vecino"
    ),

    path("superadmin/vecinos/", views.gestionar_vecinos_view, name="gestionar_vecinos"),
    path("superadmin/vecinos/<uuid:id_vecino>/editar/", views.editar_vecino_superadmin_view, name="editar_vecino_superadmin"),
]