from django.urls import include, path

urlpatterns = [
    path("", include("app.urls.auth_urls")),
    path("", include("app.urls.vecino_urls")),
    path("", include("app.urls.presidente_urls")),
    path("", include("app.urls.superadmin_urls")),
    path("", include("app.urls.certificado_urls")),
]