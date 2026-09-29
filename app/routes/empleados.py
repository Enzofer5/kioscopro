"""ABM de empleados."""
from flask import Blueprint, flash, redirect, render_template, request, url_for
from sqlalchemy import or_, select

from ..extensions import db
from ..models import Empleado
from ..services import ErrorNegocio, personas_service
from ..utils.decorators import permiso_requerido
from ..utils.helpers import hoy, parse_int

bp = Blueprint("empleados", __name__, url_prefix="/empleados")


@bp.route("/")
@permiso_requerido("empleados.gestionar")
def lista():
    texto = (request.args.get("q") or "").strip()
    estado = request.args.get("estado", "activos")
    q = select(Empleado)
    if texto:
        like = f"%{texto}%"
        q = q.where(or_(Empleado.nombre.ilike(like), Empleado.apellido.ilike(like), Empleado.dni.ilike(like), Empleado.puesto.ilike(like)))
    if estado == "activos":
        q = q.where(Empleado.activo.is_(True))
    elif estado == "inactivos":
        q = q.where(Empleado.activo.is_(False))
    paginacion = db.paginate(q.order_by(Empleado.apellido, Empleado.nombre), page=parse_int(request.args.get("page"), 1),
                             per_page=25, error_out=False)
    return render_template("empleados/lista.html", paginacion=paginacion, estado=estado)


@bp.route("/nuevo", methods=["GET", "POST"])
@permiso_requerido("empleados.gestionar")
def nuevo():
    if request.method == "POST":
        try:
            personas_service.guardar_empleado(request.form)
            flash("Empleado creado.", "success")
            return redirect(url_for("empleados.lista"))
        except ErrorNegocio as exc:
            flash(str(exc), "danger")
    return render_template("empleados/form.html", empleado=None, form=request.form, hoy=hoy())


@bp.route("/<int:empleado_id>/editar", methods=["GET", "POST"])
@permiso_requerido("empleados.gestionar")
def editar(empleado_id):
    empleado = db.get_or_404(Empleado, empleado_id)
    if request.method == "POST":
        try:
            personas_service.guardar_empleado(request.form, empleado)
            flash("Empleado actualizado.", "success")
            return redirect(url_for("empleados.lista"))
        except ErrorNegocio as exc:
            db.session.rollback()
            flash(str(exc), "danger")
    return render_template("empleados/form.html", empleado=empleado, form=request.form, hoy=hoy())


@bp.route("/<int:empleado_id>/estado", methods=["POST"])
@permiso_requerido("empleados.gestionar")
def estado(empleado_id):
    empleado = db.get_or_404(Empleado, empleado_id)
    empleado.activo = not empleado.activo
    if not empleado.activo and empleado.usuario and empleado.usuario.activo and not empleado.usuario.es_dueno:
        # Si el empleado se da de baja, su usuario también queda desactivado
        empleado.usuario.activo = False
        empleado.usuario.version_sesion += 1
        flash("También se desactivó su usuario del sistema.", "info")
    db.session.commit()
    flash(f"Empleado {'activado' if empleado.activo else 'dado de baja'}.", "success")
    return redirect(url_for("empleados.lista"))
