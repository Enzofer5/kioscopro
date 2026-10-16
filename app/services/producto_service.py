"""Productos, categorías y marcas."""
import re
from decimal import Decimal

from sqlalchemy import func, or_, select

from ..extensions import db
from ..models import Categoria, DetalleCompra, DetalleVenta, Marca, Producto, UnidadMedida
from ..utils.helpers import ahora, limpiar, parse_decimal, parse_int
from ..utils.imagenes import ImagenInvalida, borrar_imagen, guardar_imagen
from . import ErrorNegocio
from .stock_service import registrar_movimiento, validar_cantidad

FILTROS_PRODUCTO = ("codigo", "nombre", "marca_id", "categoria_id", "stock", "estado")


def hay_filtros(args):
    return any((args.get(k) or "").strip() for k in FILTROS_PRODUCTO)


def consulta_productos(args):
    """Construye la consulta a partir de los filtros de la pantalla de productos."""
    q = select(Producto)
    codigo = (args.get("codigo") or "").strip()
    nombre = (args.get("nombre") or "").strip()
    if codigo:
        q = q.where(Producto.codigo_barras.ilike(f"{codigo}%"))
    if nombre:
        for palabra in nombre.split()[:5]:
            q = q.where(or_(Producto.nombre.ilike(f"%{palabra}%"), Producto.descripcion.ilike(f"%{palabra}%")))
    if parse_int(args.get("marca_id")):
        q = q.where(Producto.marca_id == parse_int(args.get("marca_id")))
    if parse_int(args.get("categoria_id")):
        q = q.where(Producto.categoria_id == parse_int(args.get("categoria_id")))
    stock = args.get("stock")
    if stock == "bajo":
        q = q.where(Producto.stock_actual > 0, Producto.stock_actual <= Producto.stock_minimo)
    elif stock == "sin":
        q = q.where(Producto.stock_actual <= 0)
    estado = args.get("estado")
    if estado == "activos":
        q = q.where(Producto.activo.is_(True))
    elif estado == "inactivos":
        q = q.where(Producto.activo.is_(False))
    return q.order_by(Producto.nombre)


def buscar_para_pos(texto, limite=15):
    """Búsqueda rápida del POS: primero coincidencia exacta de código de barras."""
    texto = (texto or "").strip()
    if not texto:
        return []
    exacto = db.session.scalar(
        select(Producto).where(Producto.codigo_barras == texto, Producto.activo.is_(True))
    )
    if exacto:
        return [exacto]
    q = select(Producto).where(Producto.activo.is_(True))
    if texto.isdigit():
        q = q.where(or_(Producto.codigo_barras.ilike(f"{texto}%"), Producto.nombre.ilike(f"%{texto}%")))
    else:
        for palabra in texto.split()[:5]:
            q = q.where(Producto.nombre.ilike(f"%{palabra}%"))
    return db.session.scalars(q.order_by(Producto.nombre).limit(limite)).all()


def guardar_producto(form, archivos, usuario, producto=None):
    nuevo = producto is None
    nombre = limpiar(form.get("nombre"), 120)
    if not nombre:
        raise ErrorNegocio("El nombre es obligatorio.")
    codigo = re.sub(r"\s", "", form.get("codigo_barras") or "")[:32] or None
    if codigo and not re.fullmatch(r"[0-9A-Za-z\-]+", codigo):
        raise ErrorNegocio("El código de barras solo admite letras, números y guiones.")
    if codigo:
        q = select(Producto.id).where(Producto.codigo_barras == codigo)
        if not nuevo:
            q = q.where(Producto.id != producto.id)
        if db.session.scalar(q):
            raise ErrorNegocio("Ya existe otro producto con ese código de barras.")

    categoria = db.session.get(Categoria, parse_int(form.get("categoria_id"), 0))
    if categoria is None:
        raise ErrorNegocio("Seleccioná una categoría.")
    marca = None
    if parse_int(form.get("marca_id")):
        marca = db.session.get(Marca, parse_int(form.get("marca_id")))
        if marca is None:
            raise ErrorNegocio("La marca seleccionada no existe.")
    unidad = db.session.get(UnidadMedida, parse_int(form.get("unidad_id"), 0))
    if unidad is None:
        raise ErrorNegocio("Seleccioná una unidad de medida.")

    precio_compra = parse_decimal(form.get("precio_compra"), minimo=0, maximo=99_999_999)
    precio_venta = parse_decimal(form.get("precio_venta"), minimo=0, maximo=99_999_999)
    if precio_compra is None or precio_venta is None:
        raise ErrorNegocio("Revisá los precios: deben ser números mayores o iguales a cero.")
    if precio_venta < precio_compra and not form.get("confirmar_precio"):
        raise ErrorNegocio("El precio de venta es menor al de compra. Tildá «Confirmo el precio» si es correcto.")
    stock_minimo = parse_decimal(form.get("stock_minimo") or "0", minimo=0, maximo=10_000_000)
    if stock_minimo is None:
        raise ErrorNegocio("El stock mínimo debe ser 0 o más.")

    stock_inicial = Decimal(0)
    if nuevo:
        stock_inicial = parse_decimal(form.get("stock_inicial") or "0", minimo=0, maximo=10_000_000)
        if stock_inicial is None:
            raise ErrorNegocio("El stock inicial debe ser 0 o más.")

    imagen_nueva = None
    try:
        imagen_nueva = guardar_imagen(archivos.get("imagen")) if archivos else None
    except ImagenInvalida as exc:
        raise ErrorNegocio(str(exc)) from exc

    try:
        if nuevo:
            producto = Producto(creado_en=ahora(), stock_actual=0, activo=True)
            db.session.add(producto)
        producto.nombre = nombre
        producto.codigo_barras = codigo
        producto.descripcion = (form.get("descripcion") or "").strip()[:2000] or None
        producto.categoria, producto.marca, producto.unidad = categoria, marca, unidad
        producto.precio_compra, producto.precio_venta = precio_compra, precio_venta
        producto.stock_minimo = stock_minimo
        producto.actualizado_en = ahora()
        imagen_vieja = None
        if imagen_nueva:
            imagen_vieja, producto.imagen = producto.imagen, imagen_nueva
        elif form.get("quitar_imagen") and producto.imagen:
            imagen_vieja, producto.imagen = producto.imagen, None
        db.session.flush()
        if nuevo and stock_inicial > 0:
            validar_cantidad(producto, stock_inicial)
            registrar_movimiento(producto, stock_inicial, "entrada", "Stock inicial", usuario.id)
        db.session.commit()
    except Exception:
        db.session.rollback()
        borrar_imagen(imagen_nueva)
        raise
    borrar_imagen(imagen_vieja)
    return producto


def cambiar_estado(producto):
    producto.activo = not producto.activo
    producto.actualizado_en = ahora()
    db.session.commit()
    return producto.activo


# ----------------------------------------------------------- Categorías / marcas


def guardar_catalogo(modelo, nombre, item=None):
    nombre = limpiar(nombre, 60)
    if not nombre:
        raise ErrorNegocio("El nombre es obligatorio.")
    q = select(modelo.id).where(func.lower(modelo.nombre) == nombre.lower())
    if item:
        q = q.where(modelo.id != item.id)
    if db.session.scalar(q):
        raise ErrorNegocio(f"Ya existe «{nombre}».")
    if item is None:
        item = modelo(activo=True)
        db.session.add(item)
    item.nombre = nombre
    db.session.commit()
    return item


def eliminar_catalogo(modelo, item):
    """Elimina si no tiene productos; si tiene, solo se puede desactivar."""
    campo = Producto.categoria_id if modelo is Categoria else Producto.marca_id
    en_uso = db.session.scalar(select(func.count(Producto.id)).where(campo == item.id))
    if en_uso:
        raise ErrorNegocio(f"No se puede eliminar: tiene {en_uso} producto(s). Podés desactivarla.")
    db.session.delete(item)
    db.session.commit()


def producto_tiene_historial(producto_id):
    return bool(
        db.session.scalar(select(DetalleVenta.id).where(DetalleVenta.producto_id == producto_id).limit(1))
        or db.session.scalar(select(DetalleCompra.id).where(DetalleCompra.producto_id == producto_id).limit(1))
    )
