"""Inventario: historial de movimientos, movimientos manuales y alertas."""
from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user
from sqlalchemy import or_, select

from ..extensions import db
from ..models import TIPOS_MOV_STOCK, MovimientoStock, Producto, Usuario
from ..services import ErrorNegocio, reporte_service, stock_service
from ..utils.decorators import permiso_requerido
from ..utils.helpers import fin_dia, formato_cantidad, inicio_dia, parse_fecha, parse_int

bp = Blueprint("stock", __name__, url_prefix="/stock")

FILTROS = ("producto", "tipo", "desde", "hasta", "usuario_id")


@bp.route("/")
@permiso_requerido("stock.ver")
def index():
    args = request.args
    buscado = any((args.get(k) or "").strip() for k in FILTROS)
    paginacion = None
    if buscado:
        q = select(MovimientoStock).join(Producto, Producto.id == MovimientoStock.producto_id)
        texto = (args.get("producto") or "").strip()
        if texto:
            q = q.where(or_(Producto.nombre.ilike(f"%{texto}%"), Producto.codigo_barras == texto))
        if args.get("tipo") in TIPOS_MOV_STOCK:
            q = q.where(MovimientoStock.tipo == args.get("tipo"))
        if parse_fecha(args.get("desde")):
            q = q.where(MovimientoStock.fecha >= inicio_dia(parse_fecha(args.get("desde"))))
        if parse_fecha(args.get("hasta")):
            q = q.where(MovimientoStock.fecha < fin_dia(parse_fecha(args.get("hasta"))))
        if parse_int(args.get("usuario_id")):
            q = q.where(MovimientoStock.usuario_id == parse_int(args.get("usuario_id")))
        paginacion = db.paginate(q.order_by(MovimientoStock.id.desc()), page=parse_int(args.get("page"), 1),
                                 per_page=current_app.config["POR_PAGINA"], error_out=False)
    bajo, agotados = reporte_service.conteo_stock()
    usuarios = db.session.scalars(select(Usuario).order_by(Usuario.nombre)).all()
    return render_template("stock/index.html", paginacion=paginacion, buscado=buscado, bajo=bajo,
                           agotados=agotados, tipos=TIPOS_MOV_STOCK, usuarios=usuarios)


@bp.route("/movimiento", methods=["GET", "POST"])
@permiso_requerido("stock.ajustar")
def movimiento():
    if request.method == "POST":
        try:
            mov = stock_service.movimiento_manual(request.form, current_user)
            flash(f"Movimiento registrado. Stock de «{mov.producto.nombre}»: {formato_cantidad(mov.stock_nuevo)}.", "success")
            return redirect(url_for("stock.movimiento"))
        except ErrorNegocio as exc:
            flash(str(exc), "danger")
    producto = None
    pid = parse_int(request.values.get("producto_id"))
    if pid:
        producto = db.session.get(Producto, pid)
    return render_template("stock/movimiento.html", producto=producto, form=request.form)


@bp.route("/alertas/<tipo>")
@permiso_requerido("stock.ver")
def alertas(tipo):
    if tipo not in ("bajo", "agotados"):
        tipo = "bajo"
    productos = reporte_service.productos_alerta(tipo)
    bajo, agotados = reporte_service.conteo_stock()
    return render_template("stock/alertas.html", tipo=tipo, productos=productos, bajo=bajo, agotados=agotados)
