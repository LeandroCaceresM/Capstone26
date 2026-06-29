from django.urls import path
from app import views

urlpatterns = [
    path("certificado/", views.certificado_residencia_view, name="certificado_residencia"),
    path("certificado/descargar/", views.generar_certificado_view, name="generar_certificado"),
]