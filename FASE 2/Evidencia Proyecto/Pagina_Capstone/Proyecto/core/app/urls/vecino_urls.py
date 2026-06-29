from django.urls import path
from app import views

urlpatterns = [
    path("panel-vecino/", views.panel_vecino_view, name="panel_vecino"),

    path("mis-datos/", views.mis_datos_view, name="mis_datos"),
    path("mi-junta/vecinos/", views.vecinos_mi_junta_view, name="vecinos_mi_junta"),
    path("mi-junta/noticias/", views.noticias_junta_view, name="noticias_junta"),

    path("vecino/solicitudes/", views.mis_solicitudes_view, name="mis_solicitudes"),
    path("vecino/solicitudes/crear/", views.crear_solicitud_view, name="crear_solicitud"),
]