from django.urls import path
from app import views

urlpatterns = [
    path("panel-presidente/", views.panel_presidente_view, name="panel_presidente"),

    path("presidente/solicitudes/", views.solicitudes_presidente_view, name="solicitudes_presidente"),
    path("presidente/solicitudes/<uuid:id_solicitud>/cerrar/", views.cerrar_solicitud_view, name="cerrar_solicitud"),

    path("presidente/certificados/", views.certificados_presidente_view, name="certificados_presidente"),
]