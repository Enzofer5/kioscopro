"""Decoradores de autorización."""
from functools import wraps

from flask import abort, jsonify, request
from flask_login import current_user, login_required


def _quiere_json():
    return request.is_json or request.path.startswith("/api/") or "/api/" in request.path


def permiso_requerido(*codigos):
    """Exige sesión iniciada y AL MENOS uno de los permisos indicados.
    Uso: @permiso_requerido("productos.gestionar")"""

    def decorador(vista):
        @wraps(vista)
        @login_required
        def envoltura(*args, **kwargs):
            if not current_user.tiene_permiso(*codigos):
                if _quiere_json():
                    return jsonify(ok=False, error="No tenés permiso para esta acción."), 403
                abort(403)
            return vista(*args, **kwargs)

        return envoltura

    return decorador
