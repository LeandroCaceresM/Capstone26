from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static

from app import views


urlpatterns = [
    # =========================
    # ADMIN DJANGO
    # =========================
    path("admin/", admin.site.urls),

    # =========================
    # AUTENTICACIÓN
    # =========================
    path("", views.login_view, name="login"),
    path("login/", views.login_view, name="login"),
    path("registro/", views.registro_view, name="registro"),
    path("logout/", views.logout_view, name="logout"),

    # =========================
    # RECUPERAR CONTRASEÑA
    # =========================
    path("recuperar_contrasenia/", views.recuperar_contrasenia, name="recuperar_contrasenia"),
    path("enviar_recuperacion/", views.enviar_recuperacion, name="enviar_recuperacion"),
    path("cambiar_contrasenia/", views.cambiar_contrasenia, name="cambiar_contrasenia"),

    # =========================
    # SERVICIOS GENERALES
    # =========================
    path("mis-datos/", views.mis_datos_view, name="mis_datos"),
    path("mi-junta/vecinos/", views.vecinos_mi_junta_view, name="vecinos_mi_junta"),

    # =========================
    # VECINO
    # =========================
    path("panel-vecino/", views.panel_vecino_view, name="panel_vecino"),
    path("vecino/solicitudes/", views.mis_solicitudes_view, name="mis_solicitudes"),
    path("vecino/solicitudes/crear/", views.crear_solicitud_view, name="crear_solicitud"),
    path("vecino/certificado/", views.generar_certificado_view, name="generar_certificado"),

    # =========================
    # PRESIDENTE
    # =========================
    path("panel-presidente/", views.panel_presidente_view, name="panel_presidente"),
    path("presidente/solicitudes/", views.solicitudes_presidente_view, name="solicitudes_presidente"),
    path(
        "presidente/solicitudes/<uuid:id_solicitud>/cerrar/",
        views.cerrar_solicitud_view,
        name="cerrar_solicitud"
    ),
    
    path("presidente/certificados/", views.certificados_presidente_view, name="certificados_presidente"),
    # =========================
    # SUPERADMIN - PANEL
    # =========================
    path("panel-superadmin/", views.panel_superadmin_view, name="panel_superadmin"),

    # =========================
    # SUPERADMIN - GESTIÓN DE JUNTAS
    # =========================
    path("superadmin/juntas/", views.listar_juntas_view, name="listar_juntas"),
    path("superadmin/juntas/crear/", views.crear_junta_view, name="crear_junta"),
    path("superadmin/juntas/editar/<uuid:id_junta>/", views.editar_junta_view, name="editar_junta"),
    path("superadmin/juntas/eliminar/<uuid:id_junta>/", views.eliminar_junta_view, name="eliminar_junta"),

    # =========================
    # SUPERADMIN - VECINOS EN JUNTA
    # =========================
    path("superadmin/juntas/<uuid:id_junta>/vecinos/", views.vecinos_junta_view, name="vecinos_junta"),
    path(
        "superadmin/juntas/<uuid:id_junta>/vecinos/asignar/",
        views.asignar_vecino_junta_view,
        name="asignar_vecino_junta"
    ),
    path(
        "superadmin/juntas/<uuid:id_junta>/vecinos/<uuid:id_vecino>/quitar/",
        views.quitar_vecino_junta_view,
        name="quitar_vecino_junta"
    ),

    # =========================
    # SUPERADMIN - DIRECTIVA Y CARGOS
    # =========================
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

    # =========================
    # SUPERADMIN - GESTIÓN DE VECINOS
    # =========================
    path("superadmin/vecinos/", views.gestionar_vecinos_view, name="gestionar_vecinos"),
    path(
        "superadmin/vecinos/<uuid:id_vecino>/editar/",
        views.editar_vecino_superadmin_view,
        name="editar_vecino_superadmin"
    ),
]


urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)