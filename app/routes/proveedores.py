"""ABM de proveedores e historial de compras."""
from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for
from sqlalchemy import or_, select

from ..extensions import db
from ..models import Compra, Proveedor
from ..services import ErrorNegocio, personas_service
from ..utils.decorators import permiso_requerido
from ..utils.helpers import parse_int

bp = Blueprint("proveedores", __name__, url_prefix="/proveedores")


@bp.route("/")
@permiso_requerido("proveedores.gestionar")
def lista():
    texto = (request.args.get("q") or "").strip()
    estado = request.args.get("estado", "")
    buscado = bool(texto or estado)
    paginacion = None
    if buscado:
        q = select(Proveedor)
        if texto:
            like = f"%{texto}%"
            q = q.where(or_(Proveedor.razon_social.ilike(like), Proveedor.cuit.ilike(like), Proveedor.contacto.ilike(like)))
        if estado == "activos":
            q = q.where(Proveedor.activo.is_(True))
        elif estado == "inactivos":
            q = q.where(Proveedor.activo.is_(False))
        paginacion = db.paginate(q.order_by(Proveedor.razon_social), page=parse_int(request.args.get("page"), 1),
                                 per_page=current_app.config["POR_PAGINA"], error_out=False)
    return render_template("proveedores/lista.html", paginacion=paginacion, buscado=buscado)


@bp.route("/nuevo", methods=["GET", "POST"])
@permiso_requerido("proveedores.gestionar")
def nuevo():
    if request.method == "POST":
        try:
            p = personas_service.guardar_proveedor(request.form)
            flash("Proveedor creado.", "success")
            return redirect(url_for("proveedores.detalle", proveedor_id=p.id))
        except ErrorNegocio as exc:
            flash(str(exc), "danger")
    return render_template("proveedores/form.html", proveedor=None, form=request.form)


@bp.route("/<int:proveedor_id>/editar", methods=["GET", "POST"])
@permiso_requerido("proveedores.gestionar")
def editar(proveedor_id):
    proveedor = db.get_or_404(Proveedor, proveedor_id)
    if request.method == "POST":
        try:
            personas_service.guardar_proveedor(request.form, proveedor)
            flash("Proveedor actualizado.", "success")
            return redirect(url_for("proveedores.detalle", proveedor_id=proveedor.id))
        except ErrorNegocio as exc:
            db.session.rollback()
            flash(str(exc), "danger")
    return render_template("proveedores/form.html", proveedor=proveedor, form=request.form)


@bp.route("/<int:proveedor_id>")
@permiso_requerido("proveedores.gestionar")
def detalle(proveedor_id):
    proveedor = db.get_or_404(Proveedor, proveedor_id)
    compras = db.paginate(
        select(Compra).where(Compra.proveedor_id == proveedor.id).order_by(Compra.fecha.desc(), Compra.id.desc()),
        page=parse_int(request.args.get("page"), 1), per_page=15, error_out=False,
    )
    return render_template("proveedores/detalle.html", proveedor=proveedor, compras=compras,
                           stats=personas_service.estadisticas_proveedor(proveedor.id))


@bp.route("/<int:proveedor_id>/estado", methods=["POST"])
@permiso_requerido("proveedores.gestionar")
def estado(proveedor_id):
    proveedor = db.get_or_404(Proveedor, proveedor_id)
    proveedor.activo = not proveedor.activo
    db.session.commit()
    flash(f"Proveedor {'activado' if proveedor.activo else 'desactivado'}.", "success")
    return redirect(url_for("proveedores.detalle", proveedor_id=proveedor.id))
