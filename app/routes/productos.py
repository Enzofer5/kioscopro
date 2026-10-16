"""ABM de productos, categorías y marcas."""
from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user
from sqlalchemy import func, select

from ..extensions import db
from ..models import Categoria, Marca, MovimientoStock, Producto, UnidadMedida
from ..services import ErrorNegocio, producto_service
from ..utils.decorators import permiso_requerido
from ..utils.helpers import parse_int

bp = Blueprint("productos", __name__, url_prefix="/productos")

CATALOGOS = {"categorias": (Categoria, "Categorías", "categoría"), "marcas": (Marca, "Marcas", "marca")}


def _listas():
    return {
        "categorias": db.session.scalars(select(Categoria).order_by(Categoria.nombre)).all(),
        "marcas": db.session.scalars(select(Marca).order_by(Marca.nombre)).all(),
        "unidades": db.session.scalars(select(UnidadMedida).order_by(UnidadMedida.id)).all(),
    }


@bp.route("/")
@permiso_requerido("productos.ver")
def lista():
    buscado = producto_service.hay_filtros(request.args)
    paginacion = None
    if buscado:
        paginacion = db.paginate(
            producto_service.consulta_productos(request.args),
            page=parse_int(request.args.get("page"), 1),
            per_page=current_app.config["POR_PAGINA"],
            error_out=False,
        )
    return render_template("productos/lista.html", paginacion=paginacion, buscado=buscado, **_listas())


@bp.route("/<int:producto_id>")
@permiso_requerido("productos.ver")
def detalle(producto_id):
    producto = db.get_or_404(Producto, producto_id)
    movimientos = []
    if current_user.tiene_permiso("stock.ver"):
        movimientos = db.session.scalars(
            select(MovimientoStock).where(MovimientoStock.producto_id == producto.id)
            .order_by(MovimientoStock.id.desc()).limit(15)
        ).all()
    return render_template("productos/detalle.html", producto=producto, movimientos=movimientos)


@bp.route("/nuevo", methods=["GET", "POST"])
@permiso_requerido("productos.gestionar")
def nuevo():
    if request.method == "POST":
        try:
            p = producto_service.guardar_producto(request.form, request.files, current_user)
            flash(f"Producto «{p.nombre}» creado.", "success")
            if request.form.get("otro"):
                return redirect(url_for("productos.nuevo"))
            return redirect(url_for("productos.detalle", producto_id=p.id))
        except ErrorNegocio as exc:
            flash(str(exc), "danger")
        return render_template("productos/form.html", producto=None, form=request.form, **_listas())
    return render_template("productos/form.html", producto=None, form={}, **_listas())


@bp.route("/<int:producto_id>/editar", methods=["GET", "POST"])
@permiso_requerido("productos.gestionar")
def editar(producto_id):
    producto = db.get_or_404(Producto, producto_id)
    if request.method == "POST":
        try:
            producto_service.guardar_producto(request.form, request.files, current_user, producto)
            flash("Producto actualizado.", "success")
            return redirect(url_for("productos.detalle", producto_id=producto.id))
        except ErrorNegocio as exc:
            flash(str(exc), "danger")
            db.session.refresh(producto)
        return render_template("productos/form.html", producto=producto, form=request.form, **_listas())
    return render_template("productos/form.html", producto=producto, form={}, **_listas())


@bp.route("/<int:producto_id>/estado", methods=["POST"])
@permiso_requerido("productos.gestionar")
def estado(producto_id):
    producto = db.get_or_404(Producto, producto_id)
    activo = producto_service.cambiar_estado(producto)
    flash(f"Producto {'activado' if activo else 'desactivado'}.", "success")
    return redirect(request.referrer or url_for("productos.detalle", producto_id=producto.id))


# ------------------------------------------------------------ Categorías y marcas


def _catalogo(tipo):
    if tipo not in CATALOGOS:
        abort(404)
    return CATALOGOS[tipo]


@bp.route("/catalogo/<tipo>", methods=["GET", "POST"])
@permiso_requerido("productos.gestionar")
def catalogo(tipo):
    modelo, titulo, singular = _catalogo(tipo)
    if request.method == "POST":
        try:
            item = db.session.get(modelo, parse_int(request.form.get("id"), 0)) if request.form.get("id") else None
            producto_service.guardar_catalogo(modelo, request.form.get("nombre"), item)
            flash(f"{singular.capitalize()} guardada.", "success")
        except ErrorNegocio as exc:
            flash(str(exc), "danger")
        return redirect(url_for("productos.catalogo", tipo=tipo))
    campo = Producto.categoria_id if modelo is Categoria else Producto.marca_id
    conteos = dict(db.session.execute(select(campo, func.count(Producto.id)).group_by(campo)).all())
    items = db.session.scalars(select(modelo).order_by(modelo.nombre)).all()
    return render_template("productos/catalogo.html", tipo=tipo, titulo=titulo, singular=singular,
                           items=items, conteos=conteos, otros=[(k, v[1]) for k, v in CATALOGOS.items()])


@bp.route("/catalogo/<tipo>/<int:item_id>/estado", methods=["POST"])
@permiso_requerido("productos.gestionar")
def catalogo_estado(tipo, item_id):
    modelo, _, _ = _catalogo(tipo)
    item = db.get_or_404(modelo, item_id)
    item.activo = not item.activo
    db.session.commit()
    flash("Estado actualizado.", "success")
    return redirect(url_for("productos.catalogo", tipo=tipo))


@bp.route("/catalogo/<tipo>/<int:item_id>/eliminar", methods=["POST"])
@permiso_requerido("productos.gestionar")
def catalogo_eliminar(tipo, item_id):
    modelo, _, _ = _catalogo(tipo)
    item = db.get_or_404(modelo, item_id)
    try:
        producto_service.eliminar_catalogo(modelo, item)
        flash("Eliminado.", "success")
    except ErrorNegocio as exc:
        flash(str(exc), "danger")
    return redirect(url_for("productos.catalogo", tipo=tipo))
