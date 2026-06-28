from django.urls import path
from app import views

urlpatterns = [
    path("", views.login_view, name="login"),
    path("login/", views.login_view, name="login"),
    path("registro/", views.registro_view, name="registro"),
    path("logout/", views.logout_view, name="logout"),

    path("recuperar_contrasenia/", views.recuperar_contrasenia, name="recuperar_contrasenia"),
    path("cambiar_contrasenia/", views.cambiar_contrasenia, name="cambiar_contrasenia"),
    path("enviar_recuperacion/", views.enviar_recuperacion, name="enviar_recuperacion"),
]