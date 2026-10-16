"""Movimientos de stock. Toda modificación de stock pasa por aquí."""
from decimal import Decimal

from sqlalchemy import select

from ..extensions import db
from ..models import MovimientoStock, Producto
from ..utils.helpers import MILESIMA, ahora, formato_cantidad, limpiar, parse_decimal
from . import ErrorNegocio


def producto_bloqueado(producto_id):
    """Obtiene el producto con bloqueo de fila (SELECT ... FOR UPDATE en MySQL)
    para que dos ventas simultáneas no descuenten el mismo stock."""
    return db.session.scalar(
        select(Producto).where(Producto.id == producto_id).with_for_update().execution_options(populate_existing=True)
    )


def registrar_movimiento(producto, cantidad, tipo, motivo, usuario_id, venta_id=None, compra_id=None, fecha=None):
    """Aplica una variación de stock (con signo) y deja el registro histórico.
    No hace commit: lo hace el servicio que orquesta la operación."""
    cantidad = Decimal(cantidad).quantize(MILESIMA)
    if cantidad == 0:
        raise ErrorNegocio("La cantidad del movimiento no puede ser cero.")
    anterior = Decimal(producto.stock_actual or 0)
    nuevo = anterior + cantidad
    if nuevo < 0:
        raise ErrorNegocio(
            f"Stock insuficiente de «{producto.nombre}»: disponible {formato_cantidad(anterior)}, "
            f"se necesita {formato_cantidad(-cantidad)}."
        )
    producto.stock_actual = nuevo
    producto.actualizado_en = ahora()
    mov = MovimientoStock(
        producto_id=producto.id,
        tipo=tipo,
        cantidad=cantidad,
        stock_anterior=anterior,
        stock_nuevo=nuevo,
        motivo=motivo[:255],
        usuario_id=usuario_id,
        venta_id=venta_id,
        compra_id=compra_id,
        fecha=fecha or ahora(),
    )
    db.session.add(mov)
    return mov


def validar_cantidad(producto, cantidad):
    if not producto.unidad.permite_decimales and cantidad != cantidad.to_integral():
        raise ErrorNegocio(f"«{producto.nombre}» se maneja por unidades enteras.")


def movimiento_manual(form, usuario):
    """Entrada, salida o ajuste manual desde el módulo de inventario."""
    tipo = form.get("tipo")
    if tipo not in ("entrada", "salida", "ajuste"):
        raise ErrorNegocio("Tipo de movimiento inválido.")
    motivo = limpiar(form.get("motivo"), 255)
    if not motivo:
        raise ErrorNegocio("Indicá el motivo del movimiento.")
    try:
        producto_id = int(form.get("producto_id"))
    except (TypeError, ValueError):
        raise ErrorNegocio("Seleccioná un producto.") from None
    try:
        producto = producto_bloqueado(producto_id)
        if producto is None:
            raise ErrorNegocio("El producto no existe.")
        if tipo == "ajuste":
            nuevo = parse_decimal(form.get("cantidad"), minimo=0, maximo=10_000_000)
            if nuevo is None:
                raise ErrorNegocio("Ingresá el stock real contado (0 o más).")
            validar_cantidad(producto, nuevo)
            variacion = nuevo - Decimal(producto.stock_actual)
            if variacion == 0:
                raise ErrorNegocio("El stock contado coincide con el del sistema: no hay nada que ajustar.")
        else:
            cantidad = parse_decimal(form.get("cantidad"), minimo=0.001, maximo=10_000_000)
            if cantidad is None:
                raise ErrorNegocio("Ingresá una cantidad mayor a cero.")
            validar_cantidad(producto, cantidad)
            variacion = cantidad if tipo == "entrada" else -cantidad
        mov = registrar_movimiento(producto, variacion, tipo, motivo, usuario.id)
        db.session.commit()
        return mov
    except Exception:
        db.session.rollback()
        raise
