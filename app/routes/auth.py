"""Login, logout, registro inicial, recuperación y cambio de contraseña, perfil."""
from flask import Blueprint, current_app, flash, redirect, render_template, request, session, url_for
from flask_login import current_user, login_required, login_user, logout_user

from ..services import ErrorNegocio
from ..services import auth_service, usuario_service
from ..utils import rate_limit

bp = Blueprint("auth", __name__, url_prefix="/auth")


def _destino_seguro(destino):
    """Evita redirecciones abiertas: solo rutas internas."""
    if destino and destino.startswith("/") and not destino.startswith("//") and "\\" not in destino:
        return destino
    return url_for("dashboard.index")


@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))
    if request.method == "POST":
        ident = (request.form.get("usuario") or "").strip()[:120]
        ip = request.remote_addr or "?"
        cfg = current_app.config
        espera = rate_limit.bloqueado(ip, ident, cfg["LOGIN_MAX_INTENTOS"], cfg["LOGIN_BLOQUEO_MINUTOS"])
        if espera:
            flash(f"Demasiados intentos fallidos. Probá de nuevo en {espera // 60 + 1} minuto(s).", "danger")
            return render_template("auth/login.html", usuario=ident), 429
        try:
            usuario = auth_service.autenticar(ident, request.form.get("password", ""))
        except ErrorNegocio as exc:
            flash(str(exc), "danger")
            return render_template("auth/login.html", usuario=ident)
        if usuario is None:
            rate_limit.registrar_fallo(ip, ident)
            flash("Usuario o contraseña incorrectos.", "danger")
            return render_template("auth/login.html", usuario=ident)
        rate_limit.limpiar(ip, ident)
        session.clear()  # nueva sesión tras autenticar (evita fijación de sesión)
        login_user(usuario, remember=bool(request.form.get("recordar")))
        session.permanent = True
        return redirect(_destino_seguro(request.args.get("next")))
    return render_template("auth/login.html", usuario="")


@bp.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    session.clear()
    flash("Sesión cerrada.", "info")
    return redirect(url_for("auth.login"))


@bp.route("/registro-inicial", methods=["GET", "POST"])
def registro_inicial():
    if auth_service.hay_usuarios():
        return redirect(url_for("auth.login"))
    if request.method == "POST":
        try:
            usuario = auth_service.registrar_dueno(request.form)
        except ErrorNegocio as exc:
            flash(str(exc), "danger")
            return render_template("auth/registro_inicial.html", form=request.form)
        current_app.config["_SISTEMA_INICIALIZADO"] = True
        session.clear()
        login_user(usuario)
        flash("¡Listo! Tu cuenta de dueño fue creada.", "success")
        return redirect(url_for("dashboard.index"))
    return render_template("auth/registro_inicial.html", form={})


@bp.route("/recuperar", methods=["GET", "POST"])
def recuperar():
    if request.method == "POST":
        ip = request.remote_addr or "?"
        if rate_limit.bloqueado(ip, "__reset__", 5, 15):
            flash("Demasiadas solicitudes. Esperá unos minutos.", "danger")
            return render_template("auth/recuperar.html"), 429
        rate_limit.registrar_fallo(ip, "__reset__")
        auth_service.solicitar_recuperacion(request.form.get("email"))
        flash("Si el email está registrado, vas a recibir un enlace para crear una nueva contraseña. "
              "Si no llega, pedile al dueño o administrador que te asigne una contraseña temporal.", "info")
        return redirect(url_for("auth.login"))
    return render_template("auth/recuperar.html")


@bp.route("/restablecer/<token>", methods=["GET", "POST"])
def restablecer(token):
    if auth_service.token_valido(token) is None:
        flash("El enlace no es válido o ya venció.", "danger")
        return redirect(url_for("auth.recuperar"))
    if request.method == "POST":
        try:
            auth_service.restablecer_password(token, request.form.get("password"), request.form.get("password2"))
        except ErrorNegocio as exc:
            flash(str(exc), "danger")
            return render_template("auth/restablecer.html", token=token)
        flash("Contraseña actualizada. Ya podés ingresar.", "success")
        return redirect(url_for("auth.login"))
    return render_template("auth/restablecer.html", token=token)


@bp.route("/perfil", methods=["GET", "POST"])
@login_required
def perfil():
    if request.method == "POST":
        try:
            usuario_service.actualizar_perfil(current_user, request.form)
            flash("Perfil actualizado.", "success")
        except ErrorNegocio as exc:
            flash(str(exc), "danger")
        return redirect(url_for("auth.perfil"))
    return render_template("auth/perfil.html")


@bp.route("/cambiar-password", methods=["GET", "POST"])
@login_required
def cambiar_password():
    if request.method == "POST":
        try:
            auth_service.cambiar_password(
                current_user, request.form.get("actual"), request.form.get("password"), request.form.get("password2")
            )
        except ErrorNegocio as exc:
            flash(str(exc), "danger")
            return render_template("auth/cambiar_password.html")
        # La versión de sesión cambió: se vuelve a iniciar la sesión actual
        login_user(current_user._get_current_object())
        flash("Contraseña actualizada.", "success")
        return redirect(url_for("dashboard.index"))
    return render_template("auth/cambiar_password.html")
