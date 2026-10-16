"""ABM de clientes e historial de compras del cliente."""
from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user
from sqlalchemy import select

from ..extensions import db
from ..models import Cliente, Venta
from ..services import ErrorNegocio, personas_service
from ..utils.decorators import permiso_requerido
from ..utils.helpers import parse_int

bp = Blueprint("clientes", __name__, url_prefix="/clientes")


@bp.route("/")
@permiso_requerido("clientes.ver")
def lista():
    texto = (request.args.get("q") or "").strip()
    estado = request.args.get("estado", "")
    buscado = bool(texto or estado)
    paginacion = None
    if buscado:
        paginacion = db.paginate(personas_service.buscar_clientes(texto, estado),
                                 page=parse_int(request.args.get("page"), 1),
                                 per_page=current_app.config["POR_PAGINA"], error_out=False)
    return render_template("clientes/lista.html", paginacion=paginacion, buscado=buscado)


@bp.route("/nuevo", methods=["GET", "POST"])
@permiso_requerido("clientes.gestionar")
def nuevo():
    if request.method == "POST":
        try:
            c = personas_service.guardar_cliente(request.form)
            flash("Cliente creado.", "success")
            return redirect(url_for("clientes.detalle", cliente_id=c.id))
        except ErrorNegocio as exc:
            flash(str(exc), "danger")
    return render_template("clientes/form.html", cliente=None, form=request.form)


@bp.route("/<int:cliente_id>/editar", methods=["GET", "POST"])
@permiso_requerido("clientes.gestionar")
def editar(cliente_id):
    cliente = db.get_or_404(Cliente, cliente_id)
    if request.method == "POST":
        try:
            personas_service.guardar_cliente(request.form, cliente)
            flash("Cliente actualizado.", "success")
            return redirect(url_for("clientes.detalle", cliente_id=cliente.id))
        except ErrorNegocio as exc:
            db.session.rollback()
            flash(str(exc), "danger")
    return render_template("clientes/form.html", cliente=cliente, form=request.form)


@bp.route("/<int:cliente_id>")
@permiso_requerido("clientes.ver")
def detalle(cliente_id):
    cliente = db.get_or_404(Cliente, cliente_id)
    ventas = db.paginate(
        select(Venta).where(Venta.cliente_id == cliente.id).order_by(Venta.id.desc()),
        page=parse_int(request.args.get("page"), 1), per_page=15, error_out=False,
    )
    return render_template("clientes/detalle.html", cliente=cliente, ventas=ventas,
                           stats=personas_service.estadisticas_cliente(cliente.id),
                           ver_ventas=current_user.tiene_permiso("ventas.historial"))


@bp.route("/<int:cliente_id>/estado", methods=["POST"])
@permiso_requerido("clientes.gestionar")
def estado(cliente_id):
    cliente = db.get_or_404(Cliente, cliente_id)
    cliente.activo = not cliente.activo
    db.session.commit()
    flash(f"Cliente {'activado' if cliente.activo else 'desactivado'}.", "success")
    return redirect(url_for("clientes.detalle", cliente_id=cliente.id))
