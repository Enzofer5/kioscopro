"""Administración de usuarios y visualización de permisos por rol."""
from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user
from sqlalchemy import select

from ..extensions import db
from ..models import PERMISOS, Empleado, Rol, Usuario
from ..services import ErrorNegocio, usuario_service
from ..utils.decorators import permiso_requerido

bp = Blueprint("usuarios", __name__, url_prefix="/usuarios")


def _empleados_libres(usuario=None):
    empleados = db.session.scalars(select(Empleado).where(Empleado.activo.is_(True)).order_by(Empleado.apellido)).all()
    return [e for e in empleados if e.usuario is None or (usuario and e.usuario and e.usuario.id == usuario.id)]


@bp.route("/")
@permiso_requerido("usuarios.gestionar")
def lista():
    usuarios = db.session.scalars(select(Usuario).order_by(Usuario.activo.desc(), Usuario.nombre)).all()
    roles = db.session.scalars(select(Rol).order_by(Rol.id)).all()
    return render_template("usuarios/lista.html", usuarios=usuarios, roles=roles, permisos=PERMISOS)


@bp.route("/nuevo", methods=["GET", "POST"])
@permiso_requerido("usuarios.gestionar")
def nuevo():
    if request.method == "POST":
        try:
            u = usuario_service.guardar(current_user, request.form)
            flash(f"Usuario «{u.username}» creado. Deberá cambiar la contraseña en su primer ingreso.", "success")
            return redirect(url_for("usuarios.lista"))
        except ErrorNegocio as exc:
            db.session.rollback()
            flash(str(exc), "danger")
    return render_template("usuarios/form.html", usuario=None, form=request.form,
                           roles=usuario_service.roles_asignables(current_user), empleados=_empleados_libres())


@bp.route("/<int:usuario_id>/editar", methods=["GET", "POST"])
@permiso_requerido("usuarios.gestionar")
def editar(usuario_id):
    usuario = db.get_or_404(Usuario, usuario_id)
    if not usuario_service.puede_editar(current_user, usuario):
        abort(403)
    if request.method == "POST":
        try:
            usuario_service.guardar(current_user, request.form, usuario)
            flash("Usuario actualizado.", "success")
            return redirect(url_for("usuarios.lista"))
        except ErrorNegocio as exc:
            db.session.rollback()
            flash(str(exc), "danger")
    return render_template("usuarios/form.html", usuario=usuario, form=request.form,
                           roles=usuario_service.roles_asignables(current_user), empleados=_empleados_libres(usuario))


@bp.route("/<int:usuario_id>/estado", methods=["POST"])
@permiso_requerido("usuarios.gestionar")
def estado(usuario_id):
    usuario = db.get_or_404(Usuario, usuario_id)
    try:
        activo = usuario_service.cambiar_estado(current_user, usuario)
        flash(f"Usuario {'activado' if activo else 'desactivado'}.", "success")
    except ErrorNegocio as exc:
        flash(str(exc), "danger")
    return redirect(url_for("usuarios.lista"))


@bp.route("/<int:usuario_id>/reset-password", methods=["POST"])
@permiso_requerido("usuarios.gestionar")
def reset_password(usuario_id):
    usuario = db.get_or_404(Usuario, usuario_id)
    try:
        temporal = usuario_service.resetear_password(current_user, usuario)
        flash(f"Contraseña temporal de {usuario.username}: {temporal} — entregásela en persona. "
              "Deberá cambiarla al ingresar.", "warning")
    except ErrorNegocio as exc:
        flash(str(exc), "danger")
    return redirect(url_for("usuarios.lista"))
