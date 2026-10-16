"""Gastos del negocio."""
from datetime import timedelta

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user
from sqlalchemy import func, select

from ..extensions import db
from ..models import CategoriaGasto, Gasto, MetodoPago
from ..services import ErrorNegocio, gasto_service, producto_service
from ..utils.decorators import permiso_requerido
from ..utils.helpers import hoy, parse_fecha, parse_int

bp = Blueprint("gastos", __name__, url_prefix="/gastos")


def _listas():
    return {
        "categorias": db.session.scalars(select(CategoriaGasto).where(CategoriaGasto.activo.is_(True)).order_by(CategoriaGasto.nombre)).all(),
        "metodos": db.session.scalars(select(MetodoPago).where(MetodoPago.activo.is_(True)).order_by(MetodoPago.orden)).all(),
    }


@bp.route("/", methods=["GET", "POST"])
@permiso_requerido("gastos.gestionar")
def index():
    if request.method == "POST":
        try:
            gasto_service.registrar(request.form, current_user)
            flash("Gasto registrado.", "success")
            return redirect(url_for("gastos.index"))
        except ErrorNegocio as exc:
            flash(str(exc), "danger")
    desde = parse_fecha(request.args.get("desde"), hoy().replace(day=1))
    hasta = parse_fecha(request.args.get("hasta"), hoy())
    q = select(Gasto).where(Gasto.fecha >= desde, Gasto.fecha <= hasta)
    total_q = select(func.coalesce(func.sum(Gasto.monto), 0)).where(Gasto.fecha >= desde, Gasto.fecha <= hasta)
    if parse_int(request.args.get("categoria_id")):
        q = q.where(Gasto.categoria_id == parse_int(request.args.get("categoria_id")))
        total_q = total_q.where(Gasto.categoria_id == parse_int(request.args.get("categoria_id")))
    paginacion = db.paginate(q.order_by(Gasto.fecha.desc(), Gasto.id.desc()), page=parse_int(request.args.get("page"), 1),
                             per_page=25, error_out=False)
    return render_template("gastos/index.html", paginacion=paginacion, desde=desde, hasta=hasta,
                           total=db.session.scalar(total_q), hoy=hoy(), form=request.form, **_listas())


@bp.route("/<int:gasto_id>/eliminar", methods=["POST"])
@permiso_requerido("gastos.gestionar")
def eliminar(gasto_id):
    gasto = db.get_or_404(Gasto, gasto_id)
    try:
        gasto_service.eliminar(gasto)
        flash("Gasto eliminado.", "success")
    except ErrorNegocio as exc:
        flash(str(exc), "danger")
    return redirect(url_for("gastos.index"))


@bp.route("/categorias", methods=["GET", "POST"])
@permiso_requerido("gastos.gestionar")
def categorias():
    if request.method == "POST":
        try:
            item = db.session.get(CategoriaGasto, parse_int(request.form.get("id"), 0)) if request.form.get("id") else None
            producto_service.guardar_catalogo(CategoriaGasto, request.form.get("nombre"), item)
            flash("Categoría guardada.", "success")
        except ErrorNegocio as exc:
            flash(str(exc), "danger")
        return redirect(url_for("gastos.categorias"))
    items = db.session.scalars(select(CategoriaGasto).order_by(CategoriaGasto.nombre)).all()
    return render_template("gastos/categorias.html", items=items, desde=hoy() - timedelta(days=30))


@bp.route("/categorias/<int:item_id>/estado", methods=["POST"])
@permiso_requerido("gastos.gestionar")
def categoria_estado(item_id):
    item = db.get_or_404(CategoriaGasto, item_id)
    item.activo = not item.activo
    db.session.commit()
    return redirect(url_for("gastos.categorias"))
