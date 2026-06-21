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
    path("panel-presidente/", views.panel_presidente_view, name="panel_presidente"),
    path("panel-superadmin/", views.panel_superadmin_view, name="panel_superadmin"),
    ]

