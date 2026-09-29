"""App factory de KioscoPro."""
import logging
import os
import secrets

from flask import Flask, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user
from flask_wtf.csrf import CSRFError
from sqlalchemy import event
from sqlalchemy.engine import Engine
from werkzeug.middleware.proxy_fix import ProxyFix

from .config import CONFIGS
from .extensions import csrf, db, login_manager
from .utils import helpers


@event.listens_for(Engine, "connect")
def _sqlite_fk(dbapi_connection, connection_record):
    """SQLite (modo demo) no aplica claves foráneas si no se activan."""
    if dbapi_connection.__class__.__module__.startswith("sqlite3"):
        cur = dbapi_connection.cursor()
        cur.execute("PRAGMA foreign_keys=ON")
        cur.close()


def create_app(config_name=None):
    config_name = config_name or os.getenv("APP_ENV", "development")
    app = Flask(__name__)
    app.config.from_object(CONFIGS.get(config_name, CONFIGS["development"]))

    if not app.config.get("SECRET_KEY"):
        if config_name == "production":
            raise RuntimeError("Definí SECRET_KEY en el archivo .env antes de iniciar en producción.")
        app.config["SECRET_KEY"] = secrets.token_hex(32)
        app.logger.warning("SECRET_KEY no definida: se generó una temporal (las sesiones se pierden al reiniciar).")

    if os.getenv("BEHIND_PROXY", "0") == "1":
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)

    _registrar_blueprints(app)
    _registrar_hooks(app)
    _registrar_filtros(app)
    _registrar_errores(app)

    from .cli import registrar_comandos

    registrar_comandos(app)
    return app


def _registrar_blueprints(app):
    from .routes.auth import bp as auth_bp
    from .routes.caja import bp as caja_bp
    from .routes.clientes import bp as clientes_bp
    from .routes.compras import bp as compras_bp
    from .routes.dashboard import bp as dashboard_bp
    from .routes.empleados import bp as empleados_bp
    from .routes.gastos import bp as gastos_bp
    from .routes.productos import bp as productos_bp
    from .routes.proveedores import bp as proveedores_bp
    from .routes.reportes import bp as reportes_bp
    from .routes.stock import bp as stock_bp
    from .routes.usuarios import bp as usuarios_bp
    from .routes.ventas import bp as ventas_bp

    for bp in (auth_bp, dashboard_bp, ventas_bp, productos_bp, stock_bp, compras_bp, proveedores_bp,
               clientes_bp, caja_bp, gastos_bp, empleados_bp, usuarios_bp, reportes_bp):
        app.register_blueprint(bp)


def _registrar_hooks(app):
    from .models import Usuario

    @login_manager.user_loader
    def cargar_usuario(identificador):
        try:
            uid, version = str(identificador).split(":")
            usuario = db.session.get(Usuario, int(uid))
        except (ValueError, TypeError):
            return None
        # Si cambió la contraseña o se desactivó, la sesión deja de valer
        if usuario is None or str(usuario.version_sesion) != version or not usuario.activo:
            return None
        return usuario

    @app.before_request
    def controles_globales():
        endpoint = request.endpoint or ""
        if endpoint == "static":
            return None
        # Primer uso: si no hay usuarios, ir al registro inicial del dueño
        if not app.config.get("_SISTEMA_INICIALIZADO"):
            from .services.auth_service import hay_usuarios

            try:
                if hay_usuarios():
                    app.config["_SISTEMA_INICIALIZADO"] = True
                elif endpoint != "auth.registro_inicial":
                    return redirect(url_for("auth.registro_inicial"))
            except Exception:  # base sin tablas
                app.logger.exception("No se pudo consultar la base de datos")
                return render_template("errors/error.html", codigo=500,
                                       titulo="Base de datos no disponible",
                                       mensaje="Revisá la conexión y ejecutá 'flask init-db'."), 500
        # Contraseña temporal: obligar a cambiarla
        if (current_user.is_authenticated and current_user.debe_cambiar_password
                and endpoint not in ("auth.cambiar_password", "auth.logout")):
            flash("Por seguridad, cambiá tu contraseña temporal antes de continuar.", "warning")
            return redirect(url_for("auth.cambiar_password"))
        return None

    @app.context_processor
    def contexto_global():
        from .services.caja_service import caja_abierta

        caja = None
        if current_user.is_authenticated:
            try:
                caja = caja_abierta()
            except Exception:
                caja = None
        return {
            "negocio": {
                "nombre": app.config["NEGOCIO_NOMBRE"],
                "direccion": app.config["NEGOCIO_DIRECCION"],
                "cuit": app.config["NEGOCIO_CUIT"],
                "telefono": app.config["NEGOCIO_TELEFONO"],
            },
            "caja_actual": caja,
            "ahora": helpers.ahora,
        }

    @app.after_request
    def cabeceras_seguridad(resp):
        resp.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: blob:; font-src 'self' data:; connect-src 'self'; "
            "frame-ancestors 'self'; form-action 'self'; base-uri 'self'; object-src 'none'",
        )
        resp.headers.setdefault("X-Content-Type-Options", "nosniff")
        resp.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
        resp.headers.setdefault("Referrer-Policy", "same-origin")
        resp.headers.setdefault("Permissions-Policy", "geolocation=(), microphone=()")
        if current_user.is_authenticated and request.endpoint != "static":
            resp.headers.setdefault("Cache-Control", "no-store")
        return resp


def _registrar_filtros(app):
    app.jinja_env.filters["moneda"] = helpers.formato_moneda
    app.jinja_env.filters["cantidad"] = helpers.formato_cantidad
    app.jinja_env.filters["fecha"] = helpers.formato_fecha
    app.jinja_env.filters["solo_fecha"] = lambda v: helpers.formato_fecha(v, con_hora=False)
    app.jinja_env.filters["pct"] = lambda v: f"{float(v or 0):.1f}%".replace(".", ",")
    app.jinja_env.filters["num"] = lambda v: float(v or 0)

    def url_con(**cambios):
        """URL de la vista actual conservando los filtros y cambiando algunos parámetros."""
        args = request.args.to_dict()
        for clave, valor in cambios.items():
            if valor is None:
                args.pop(clave, None)
            else:
                args[clave] = valor
        return url_for(request.endpoint, **(request.view_args or {}), **args)

    app.jinja_env.globals["url_con"] = url_con


def _registrar_errores(app):
    def _responder(codigo, titulo, mensaje):
        if request.is_json or "/api/" in request.path:
            return jsonify(ok=False, error=mensaje), codigo
        return render_template("errors/error.html", codigo=codigo, titulo=titulo, mensaje=mensaje), codigo

    @app.errorhandler(403)
    def prohibido(_e):
        return _responder(403, "Acceso denegado", "Tu rol no tiene permiso para ver esta sección.")

    @app.errorhandler(404)
    def no_encontrado(_e):
        return _responder(404, "No encontrado", "La página o el registro que buscás no existe.")

    @app.errorhandler(413)
    def muy_grande(_e):
        return _responder(413, "Archivo muy grande", "El archivo supera el máximo permitido (4 MB).")

    @app.errorhandler(CSRFError)
    def csrf_error(_e):
        return _responder(400, "Sesión vencida", "El formulario venció. Recargá la página e intentá de nuevo.")

    @app.errorhandler(500)
    def error_interno(_e):
        db.session.rollback()
        return _responder(500, "Error interno", "Ocurrió un error inesperado. Ya quedó registrado.")
