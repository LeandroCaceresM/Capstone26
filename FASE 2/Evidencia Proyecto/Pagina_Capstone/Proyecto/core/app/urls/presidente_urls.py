from django.urls import path
from app import views

urlpatterns = [
    path("panel-presidente/", views.panel_presidente_view, name="panel_presidente"),

    path("presidente/solicitudes/", views.solicitudes_presidente_view, name="solicitudes_presidente"),
    path("presidente/solicitudes/<uuid:id_solicitud>/cerrar/", views.cerrar_solicitud_view, name="cerrar_solicitud"),

    path("presidente/certificados/", views.certificados_presidente_view, name="certificados_presidente"),
    
    path(
        "presidente/noticias/<uuid:id_noticia>/editar/",
        views.editar_noticia_view,
        name="editar_noticia"
    ),
    path(
        "presidente/noticias/<uuid:id_noticia>/eliminar/",
        views.eliminar_noticia_view,
        name="eliminar_noticia"
    ),
    path(
        "presidente/noticias/",
        views.gestionar_noticias_view,
        name="gestionar_noticias"
    ),
        
    path("presidente/eventos/", views.gestionar_eventos_view, name="gestionar_eventos"),
    
    path(
        "presidente/eventos/<uuid:id_evento>/editar/",
        views.editar_evento_view,
        name="editar_evento"
    ),
    path(
        "presidente/eventos/<uuid:id_evento>/eliminar/",
        views.eliminar_evento_view,
        name="eliminar_evento"
    ),
]

