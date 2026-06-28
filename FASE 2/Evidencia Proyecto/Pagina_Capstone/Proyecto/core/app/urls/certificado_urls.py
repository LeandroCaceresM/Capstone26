from django.urls import path
from app import views

urlpatterns = [
    path("vecino/certificado/", views.generar_certificado_view, name="generar_certificado"),
]