"""Punto de venta: confirmación de ventas, anulaciones y devoluciones."""
from decimal import Decimal

from flask import current_app
from sqlalchemy import select

from ..extensions import db
from ..models import (
    ESTADO_ANULADA,
    ESTADO_COMPLETADA,
    ESTADO_DEVUELTA,
    AnulacionVenta,
    Cliente,
    DetalleVenta,
    MetodoPago,
    Pago,
    Venta,
)
from ..utils.helpers import ahora, limpiar, parse_decimal, parse_int, redondear
from . import ErrorNegocio
from . import caja_service
from .stock_service import producto_bloqueado, registrar_movimiento, validar_cantidad

MAX_ITEMS = 200


def _leer_items(items):
    """Valida la estructura enviada por el POS y agrupa productos repetidos."""
    if not isinstance(items, list) or not items:
        raise ErrorNegocio("El carrito está vacío.")
    if len(items) > MAX_ITEMS:
        raise ErrorNegocio(f"Máximo {MAX_ITEMS} ítems por venta.")
    agrupados = {}
    for item in items:
        if not isinstance(item, dict):
            raise ErrorNegocio("Formato de carrito inválido.")
        pid = parse_int(item.get("producto_id"))
        cantidad = parse_decimal(item.get("cantidad"), minimo=0.001, maximo=100_000)
        descuento_pct = parse_decimal(item.get("descuento_pct", 0), default=None, minimo=0, maximo=100)
        if not pid or cantidad is None:
            raise ErrorNegocio("Hay un ítem con cantidad inválida.")
        if descuento_pct is None:
            raise ErrorNegocio("El descuento por ítem debe estar entre 0 y 100%.")
        if pid in agrupados:
            agrupados[pid]["cantidad"] += cantidad
        else:
            agrupados[pid] = {"cantidad": cantidad, "descuento_pct": descuento_pct}
    return agrupados


def confirmar_venta(datos, usuario):
    """Registra la venta completa en UNA transacción:
    venta + detalle + pago + descuento de stock + movimiento de caja."""
    try:
        items = _leer_items(datos.get("items"))

        metodo = db.session.scalar(
            select(MetodoPago).where(MetodoPago.codigo == str(datos.get("metodo_pago", "")), MetodoPago.activo.is_(True))
        )
        if metodo is None:
            raise ErrorNegocio("Seleccioná un método de pago válido.")

        cliente = None
        if parse_int(datos.get("cliente_id")):
            cliente = db.session.get(Cliente, parse_int(datos.get("cliente_id")))
            if cliente is None or not cliente.activo:
                raise ErrorNegocio("El cliente seleccionado no existe o está inactivo.")

        caja = caja_service.caja_abierta(bloquear=True)
        if caja is None and current_app.config["REQUIERE_CAJA_ABIERTA"]:
            raise ErrorNegocio("No hay una caja abierta. Abrí la caja para poder vender.")

        momento = ahora()
        venta = Venta(
            fecha=momento,
            usuario_id=usuario.id,
            cliente_id=cliente.id if cliente else None,
            caja_id=caja.id if caja else None,
            subtotal=0,
            descuento=0,
            total=0,
            estado=ESTADO_COMPLETADA,
            observaciones=limpiar(datos.get("observaciones"), 255),
        )
        db.session.add(venta)
        db.session.flush()  # obtiene venta.id

        bruto_total = Decimal("0")
        descuento_items = Decimal("0")
        lineas = []
        # Orden por id para bloquear filas siempre en el mismo orden (evita deadlocks)
        for pid in sorted(items):
            item = items[pid]
            producto = producto_bloqueado(pid)
            if producto is None or not producto.activo:
                raise ErrorNegocio("Uno de los productos ya no está disponible.")
            validar_cantidad(producto, item["cantidad"])
            precio = Decimal(producto.precio_venta)  # el precio SIEMPRE sale de la base
            bruto = redondear(item["cantidad"] * precio)
            desc = redondear(bruto * item["descuento_pct"] / 100)
            bruto_total += bruto
            descuento_items += desc
            detalle = DetalleVenta(
                venta_id=venta.id,
                producto_id=producto.id,
                cantidad=item["cantidad"],
                precio_unitario=precio,
                costo_unitario=producto.precio_compra,
                descuento=desc,
                subtotal=bruto - desc,
            )
            db.session.add(detalle)
            lineas.append((producto, item["cantidad"]))

        neto_items = bruto_total - descuento_items
        tipo_desc = datos.get("descuento_tipo") or "porcentaje"
        valor_desc = parse_decimal(datos.get("descuento_valor") or 0, default=None, minimo=0)
        if valor_desc is None or tipo_desc not in ("porcentaje", "monto"):
            raise ErrorNegocio("Descuento general inválido.")
        if tipo_desc == "porcentaje":
            if valor_desc > 100:
                raise ErrorNegocio("El descuento no puede superar el 100%.")
            descuento_general = redondear(neto_items * valor_desc / 100)
        else:
            if valor_desc > neto_items:
                raise ErrorNegocio("El descuento no puede superar el subtotal.")
            descuento_general = redondear(valor_desc)

        total = neto_items - descuento_general
        if total <= 0:
            raise ErrorNegocio("El total de la venta debe ser mayor a cero.")

        venta.subtotal = bruto_total
        venta.descuento = descuento_items + descuento_general
        venta.total = total

        recibido = None
        if metodo.es_efectivo and datos.get("monto_recibido") not in (None, ""):
            recibido = parse_decimal(datos.get("monto_recibido"), minimo=0)
            if recibido is None or recibido < total:
                raise ErrorNegocio("El monto recibido es menor al total.")
        db.session.add(Pago(venta_id=venta.id, metodo_pago_id=metodo.id, monto=total, monto_recibido=recibido))

        for producto, cantidad in lineas:
            registrar_movimiento(producto, -cantidad, "venta", f"Venta #{venta.id}", usuario.id, venta_id=venta.id, fecha=momento)

        if caja:
            caja_service.registrar_movimiento(caja, "venta", f"Venta #{venta.id}", total, metodo.id, usuario.id, venta_id=venta.id)

        db.session.commit()
        return venta
    except Exception:
        db.session.rollback()
        raise


def anular_venta(venta_id, form, usuario):
    """Anulación (error de carga) o devolución (el cliente devuelve la mercadería).
    La venta NO se borra: cambia de estado y se registra la contrapartida."""
    tipo = form.get("tipo")
    if tipo not in ("anulacion", "devolucion"):
        raise ErrorNegocio("Tipo de operación inválido.")
    motivo = limpiar(form.get("motivo"), 255)
    if not motivo or len(motivo) < 5:
        raise ErrorNegocio("Indicá el motivo (mínimo 5 caracteres).")
    reintegra = True if tipo == "anulacion" else bool(form.get("reintegra_stock"))
    try:
        venta = db.session.scalar(select(Venta).where(Venta.id == venta_id).with_for_update())
        if venta is None:
            raise ErrorNegocio("La venta no existe.")
        if venta.estado != ESTADO_COMPLETADA:
            raise ErrorNegocio("La venta ya fue anulada o devuelta.")
        caja = caja_service.caja_abierta(bloquear=True)
        if caja is None:
            raise ErrorNegocio("Abrí la caja para registrar la salida del dinero.")

        etiqueta = "Anulación" if tipo == "anulacion" else "Devolución"
        efectivo_a_devolver = sum((p.monto for p in venta.pagos if p.metodo.es_efectivo), Decimal(0))
        if efectivo_a_devolver > 0 and efectivo_a_devolver > caja_service.resumen(caja)["esperado"]:
            raise ErrorNegocio("No hay suficiente efectivo en caja para devolver el dinero.")

        momento = ahora()
        if reintegra:
            for detalle in sorted(venta.detalles, key=lambda d: d.producto_id):
                producto = producto_bloqueado(detalle.producto_id)
                registrar_movimiento(
                    producto, detalle.cantidad, "anulacion", f"{etiqueta} venta #{venta.id}", usuario.id,
                    venta_id=venta.id, fecha=momento,
                )
        for pago in venta.pagos:
            caja_service.registrar_movimiento(
                caja, "anulacion", f"{etiqueta} venta #{venta.id}", pago.monto, pago.metodo_pago_id, usuario.id,
                venta_id=venta.id,
            )
        venta.estado = ESTADO_ANULADA if tipo == "anulacion" else ESTADO_DEVUELTA
        db.session.add(
            AnulacionVenta(
                venta_id=venta.id, tipo=tipo, motivo=motivo, reintegra_stock=reintegra,
                usuario_id=usuario.id, caja_id=caja.id, fecha=momento,
            )
        )
        db.session.commit()
        return venta
    except Exception:
        db.session.rollback()
        raise
