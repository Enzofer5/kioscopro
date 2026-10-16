"""Punto de venta, historial, detalle, comprobante y anulaciones."""
from flask import Blueprint, abort, current_app, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user
from sqlalchemy import or_, select

from ..extensions import db
from ..models import ESTADOS_VENTA, Cliente, MetodoPago, Pago, Usuario, Venta
from ..services import ErrorNegocio, caja_service, personas_service, producto_service, venta_service
from ..utils.decorators import permiso_requerido
from ..utils.helpers import fin_dia, formato_moneda, inicio_dia, parse_fecha, parse_int

bp = Blueprint("ventas", __name__, url_prefix="/ventas")


def _metodos():
    return db.session.scalars(select(MetodoPago).where(MetodoPago.activo.is_(True)).order_by(MetodoPago.orden)).all()


# ------------------------------------------------------------------ POS


@bp.route("/pos")
@permiso_requerido("ventas.crear")
def pos():
    return render_template(
        "ventas/pos.html",
        metodos=_metodos(),
        caja=caja_service.caja_abierta(),
        requiere_caja=current_app.config["REQUIERE_CAJA_ABIERTA"],
    )


@bp.route("/api/productos")
@permiso_requerido("ventas.crear", "productos.ver", "compras.gestionar", "stock.ajustar")
def api_productos():
    productos = producto_service.buscar_para_pos(request.args.get("q", "")[:60])
    ver_costo = current_user.tiene_permiso("compras.gestionar")  # el costo es dato sensible
    resultado = []
    for p in productos:
        item = p.to_pos()
        if ver_costo:
            item["costo"] = float(p.precio_compra)
        resultado.append(item)
    return jsonify(ok=True, productos=resultado)


@bp.route("/api/clientes")
@permiso_requerido("ventas.crear")
def api_clientes():
    texto = (request.args.get("q") or "").strip()[:60]
    if len(texto) < 2:
        return jsonify(ok=True, clientes=[])
    like = f"%{texto}%"
    clientes = db.session.scalars(
        select(Cliente)
        .where(Cliente.activo.is_(True), or_(Cliente.nombre.ilike(like), Cliente.apellido.ilike(like), Cliente.dni.ilike(like)))
        .order_by(Cliente.apellido)
        .limit(10)
    ).all()
    return jsonify(ok=True, clientes=[{"id": c.id, "nombre": c.nombre_completo, "dni": c.dni or ""} for c in clientes])


@bp.route("/api/clientes", methods=["POST"])
@permiso_requerido("clientes.gestionar")
def api_crear_cliente():
    try:
        c = personas_service.guardar_cliente(request.get_json(silent=True) or {})
    except ErrorNegocio as exc:
        return jsonify(ok=False, error=str(exc)), 400
    return jsonify(ok=True, cliente={"id": c.id, "nombre": c.nombre_completo, "dni": c.dni or ""})


@bp.route("/api/confirmar", methods=["POST"])
@permiso_requerido("ventas.crear")
def api_confirmar():
    datos = request.get_json(silent=True)
    if not isinstance(datos, dict):
        return jsonify(ok=False, error="Solicitud inválida."), 400
    try:
        venta = venta_service.confirmar_venta(datos, current_user)
    except ErrorNegocio as exc:
        return jsonify(ok=False, error=str(exc)), 400
    pago = venta.pagos[0]
    return jsonify(
        ok=True,
        venta_id=venta.id,
        total=float(venta.total),
        total_fmt=formato_moneda(venta.total),
        vuelto_fmt=formato_moneda(pago.vuelto) if pago.vuelto is not None else None,
        comprobante=url_for("ventas.comprobante", venta_id=venta.id),
    )


@bp.route("/<int:venta_id>/comprobante")
@permiso_requerido("ventas.crear", "ventas.historial")
def comprobante(venta_id):
    venta = db.get_or_404(Venta, venta_id)
    if venta.usuario_id != current_user.id and not current_user.tiene_permiso("ventas.historial"):
        abort(403)
    return render_template("ventas/comprobante.html", venta=venta)


# ------------------------------------------------------------------ Historial

FILTROS = ("numero", "fecha", "desde", "hasta", "usuario_id", "cliente", "metodo", "estado")


@bp.route("/historial")
@permiso_requerido("ventas.historial")
def historial():
    args = request.args
    buscado = any((args.get(k) or "").strip() for k in FILTROS)
    paginacion = None
    if buscado:
        q = select(Venta)
        numero = parse_int(args.get("numero"))
        if numero:
            q = q.where(Venta.id == numero)
        fecha = parse_fecha(args.get("fecha"))
        if fecha:
            q = q.where(Venta.fecha >= inicio_dia(fecha), Venta.fecha < fin_dia(fecha))
        desde, hasta = parse_fecha(args.get("desde")), parse_fecha(args.get("hasta"))
        if desde:
            q = q.where(Venta.fecha >= inicio_dia(desde))
        if hasta:
            q = q.where(Venta.fecha < fin_dia(hasta))
        if parse_int(args.get("usuario_id")):
            q = q.where(Venta.usuario_id == parse_int(args.get("usuario_id")))
        cliente = (args.get("cliente") or "").strip()
        if cliente:
            like = f"%{cliente}%"
            q = q.join(Cliente, Cliente.id == Venta.cliente_id).where(
                or_(Cliente.nombre.ilike(like), Cliente.apellido.ilike(like), Cliente.dni.ilike(like))
            )
        if args.get("metodo"):
            q = q.where(Venta.id.in_(
                select(Pago.venta_id).join(MetodoPago).where(MetodoPago.codigo == args.get("metodo"))
            ))
        if args.get("estado") in ESTADOS_VENTA:
            q = q.where(Venta.estado == args.get("estado"))
        paginacion = db.paginate(q.order_by(Venta.id.desc()), page=parse_int(args.get("page"), 1),
                                 per_page=current_app.config["POR_PAGINA"], error_out=False)
    usuarios = db.session.scalars(select(Usuario).order_by(Usuario.nombre)).all()
    return render_template("ventas/historial.html", paginacion=paginacion, buscado=buscado,
                           usuarios=usuarios, metodos=_metodos(), estados=ESTADOS_VENTA)


@bp.route("/<int:venta_id>")
@permiso_requerido("ventas.historial")
def detalle(venta_id):
    venta = db.get_or_404(Venta, venta_id)
    return render_template("ventas/detalle.html", venta=venta)


@bp.route("/<int:venta_id>/anular", methods=["POST"])
@permiso_requerido("ventas.anular")
def anular(venta_id):
    try:
        venta = venta_service.anular_venta(venta_id, request.form, current_user)
        flash(f"Venta #{venta.id} {venta.estado}. Se registró el movimiento en caja.", "success")
    except ErrorNegocio as exc:
        flash(str(exc), "danger")
    return redirect(url_for("ventas.detalle", venta_id=venta_id))
