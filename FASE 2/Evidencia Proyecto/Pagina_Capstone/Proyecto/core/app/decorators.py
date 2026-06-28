from functools import wraps

from django.contrib import messages
from django.shortcuts import redirect


def login_required_custom(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.session.get("vecino_id"):
            return redirect("login")

        return view_func(request, *args, **kwargs)

    return wrapper


def role_required(*roles):
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):

            if not request.session.get("vecino_id"):
                return redirect("login")

            rol = request.session.get("rol")

            if rol not in roles:

                messages.error(
                    request,
                    "No tienes permiso para acceder a esa sección."
                )

                if rol == "Usuario":
                    return redirect("panel_vecino")

                if rol == "Admin":
                    return redirect("panel_presidente")

                if rol == "Superadmin":
                    return redirect("panel_superadmin")

                return redirect("login")

            return view_func(request, *args, **kwargs)

        return wrapper

    return decorator