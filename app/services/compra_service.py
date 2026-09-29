"""Compras a proveedores: ingreso de mercadería y actualización de costos."""
from decimal import Decimal

from sqlalchemy import select

from ..extensions import db
from ..models import Compra, DetalleCompra, Proveedor
from ..utils.helpers import ahora, hoy, limpiar, parse_decimal, parse_fecha, parse_int, redondear
from . import ErrorNegocio
from .stock_service import producto_bloqueado, registrar_movimiento, validar_cantidad


def registrar_compra(datos, usuario):
    try:
        proveedor = db.session.get(Proveedor, parse_int(datos.get("proveedor_id"), 0))
        if proveedor is None or not proveedor.activo:
            raise ErrorNegocio("Seleccioná un proveedor activo.")
        fecha = parse_fecha(datos.get("fecha"))
        if fecha is None:
            raise ErrorNegocio("Ingresá la fecha de la compra.")
        if fecha > hoy():
            raise ErrorNegocio("La fecha de la compra no puede ser futura.")
        numero = limpiar(datos.get("numero_comprobante"), 40)
        if numero and db.session.scalar(
            select(Compra.id).where(Compra.proveedor_id == proveedor.id, Compra.numero_comprobante == numero)
        ):
            raise ErrorNegocio(f"Ya se registró el comprobante {numero} de este proveedor.")

        items = datos.get("items")
        if not isinstance(items, list) or not items:
            raise ErrorNegocio("Agregá al menos un producto.")
        if len(items) > 300:
            raise ErrorNegocio("Máximo 300 ítems por compra.")
        agrupados = {}
        for item in items:
            if not isinstance(item, dict):
                raise ErrorNegocio("Formato inválido.")
            pid = parse_int(item.get("producto_id"))
            cantidad = parse_decimal(item.get("cantidad"), minimo=0.001, maximo=10_000_000)
            precio = parse_decimal(item.get("precio"), minimo=0, maximo=99_999_999)
            if not pid or cantidad is None or precio is None:
                raise ErrorNegocio("Revisá cantidades y precios: deben ser números positivos.")
            if pid in agrupados:
                raise ErrorNegocio("Hay un producto repetido en la compra. Unificá las cantidades.")
            agrupados[pid] = (cantidad, redondear(precio))

        actualizar_costos = bool(datos.get("actualizar_costos"))
        momento = ahora()
        compra = Compra(
            proveedor_id=proveedor.id,
            usuario_id=usuario.id,
            fecha=fecha,
            numero_comprobante=numero,
            total=0,
            observaciones=limpiar(datos.get("observaciones"), 255),
            creado_en=momento,
        )
        db.session.add(compra)
        db.session.flush()

        total = Decimal("0")
        for pid in sorted(agrupados):
            cantidad, precio = agrupados[pid]
            producto = producto_bloqueado(pid)
            if producto is None:
                raise ErrorNegocio("Uno de los productos no existe.")
            validar_cantidad(producto, cantidad)
            subtotal = redondear(cantidad * precio)
            total += subtotal
            db.session.add(
                DetalleCompra(compra_id=compra.id, producto_id=pid, cantidad=cantidad, precio_unitario=precio, subtotal=subtotal)
            )
            registrar_movimiento(
                producto, cantidad, "compra", f"Compra #{compra.id} - {proveedor.razon_social}"[:255], usuario.id,
                compra_id=compra.id, fecha=momento,
            )
            if actualizar_costos:
                producto.precio_compra = precio
        compra.total = total
        db.session.commit()
        return compra
    except Exception:
        db.session.rollback()
        raise
