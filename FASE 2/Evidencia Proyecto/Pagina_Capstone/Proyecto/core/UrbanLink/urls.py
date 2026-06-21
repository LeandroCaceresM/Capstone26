from django.contrib import admin
from django.urls import include, path
from app import views

urlpatterns = [
    #Vista para admin.
    path("admin/", admin.site.urls),
    #Vista Usuarios
    path('', views.home_view, name='home'),
    path('login/', views.login_view, name='login'),
    path('registro/', views.registro_view, name='registro'),
    path('logout/', views.logout_view, name='logout'),
    
    path("panel-vecino/", views.panel_vecino_view, name="panel_vecino"),
    
    #Vistas de ADMIN
    path("panel-presidente/", views.panel_presidente_view, name="panel_presidente"),
    
    #Vistas de SUPERADMIN
    path("panel-superadmin/", views.panel_superadmin_view, name="panel_superadmin"),

    path("superadmin/juntas/", views.listar_juntas_view, name="listar_juntas"),
    path("superadmin/juntas/crear/", views.crear_junta_view, name="crear_junta"),
    path("superadmin/juntas/editar/<uuid:id_junta>/", views.editar_junta_view, name="editar_junta"),
    path("superadmin/juntas/eliminar/<uuid:id_junta>/", views.eliminar_junta_view, name="eliminar_junta"),

    path("superadmin/asignar-cargo/", views.asignar_cargo_view, name="asignar_cargo"),
    path("superadmin/juntas/<uuid:id_junta>/vecinos/", views.vecinos_junta_view, name="vecinos_junta"),
    path("superadmin/juntas/<uuid:id_junta>/vecinos/asignar/", views.asignar_vecino_junta_view, name="asignar_vecino_junta"),   
    path(
        "superadmin/juntas/<uuid:id_junta>/vecinos/<uuid:id_vecino>/editar/",
        views.editar_vecino_junta_view,
        name="editar_vecino_junta"
    ),
    path(
        "superadmin/juntas/<uuid:id_junta>/vecinos/<uuid:id_vecino>/quitar/",
        views.quitar_vecino_junta_view,
        name="quitar_vecino_junta"
    ),
    ]


