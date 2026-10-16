"""Compras a proveedores."""
from flask import Blueprint, current_app, jsonify, render_template, request, url_for
from flask_login import current_user
from sqlalchemy import select

from ..extensions import db
from ..models import Compra, Proveedor
from ..services import ErrorNegocio, compra_service
from ..utils.decorators import permiso_requerido
from ..utils.helpers import hoy, parse_fecha, parse_int

bp = Blueprint("compras", __name__, url_prefix="/compras")

FILTROS = ("proveedor_id", "comprobante", "desde", "hasta", "numero")


@bp.route("/")
@permiso_requerido("compras.gestionar")
def lista():
    args = request.args
    buscado = any((args.get(k) or "").strip() for k in FILTROS)
    paginacion = None
    if buscado:
        q = select(Compra)
        if parse_int(args.get("numero")):
            q = q.where(Compra.id == parse_int(args.get("numero")))
        if parse_int(args.get("proveedor_id")):
            q = q.where(Compra.proveedor_id == parse_int(args.get("proveedor_id")))
        if (args.get("comprobante") or "").strip():
            q = q.where(Compra.numero_comprobante.ilike(f"%{args.get('comprobante').strip()}%"))
        if parse_fecha(args.get("desde")):
            q = q.where(Compra.fecha >= parse_fecha(args.get("desde")))
        if parse_fecha(args.get("hasta")):
            q = q.where(Compra.fecha <= parse_fecha(args.get("hasta")))
        paginacion = db.paginate(q.order_by(Compra.fecha.desc(), Compra.id.desc()), page=parse_int(args.get("page"), 1),
                                 per_page=current_app.config["POR_PAGINA"], error_out=False)
    proveedores = db.session.scalars(select(Proveedor).order_by(Proveedor.razon_social)).all()
    return render_template("compras/lista.html", paginacion=paginacion, buscado=buscado, proveedores=proveedores)


@bp.route("/nueva")
@permiso_requerido("compras.gestionar")
def nueva():
    proveedores = db.session.scalars(
        select(Proveedor).where(Proveedor.activo.is_(True)).order_by(Proveedor.razon_social)
    ).all()
    return render_template("compras/nueva.html", proveedores=proveedores, hoy=hoy(),
                           proveedor_id=parse_int(request.args.get("proveedor_id")))


@bp.route("/api/confirmar", methods=["POST"])
@permiso_requerido("compras.gestionar")
def api_confirmar():
    datos = request.get_json(silent=True)
    if not isinstance(datos, dict):
        return jsonify(ok=False, error="Solicitud inválida."), 400
    try:
        compra = compra_service.registrar_compra(datos, current_user)
    except ErrorNegocio as exc:
        return jsonify(ok=False, error=str(exc)), 400
    return jsonify(ok=True, compra_id=compra.id, url=url_for("compras.detalle", compra_id=compra.id))


@bp.route("/<int:compra_id>")
@permiso_requerido("compras.gestionar")
def detalle(compra_id):
    return render_template("compras/detalle.html", compra=db.get_or_404(Compra, compra_id))
