"""Apertura, movimientos, arqueo y cierre de caja."""
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from ..extensions import db
from ..models import TIPOS_CAJA_SALIDA, Caja, MetodoPago, MovimientoCaja, Venta
from ..utils.helpers import ahora, limpiar, parse_decimal
from . import ErrorNegocio

TIPOS_MANUALES = {"ingreso": "Ingreso manual", "egreso": "Egreso", "retiro": "Retiro de dinero"}


def caja_abierta(bloquear=False):
    q = select(Caja).where(Caja.abierta.is_(True))
    if bloquear:
        q = q.with_for_update()
    return db.session.scalar(q)


def metodo_efectivo():
    metodo = db.session.scalar(select(MetodoPago).where(MetodoPago.es_efectivo.is_(True)).order_by(MetodoPago.orden))
    if metodo is None:
        raise ErrorNegocio("No hay un método de pago en efectivo configurado.")
    return metodo


def abrir(form, usuario):
    if caja_abierta():
        raise ErrorNegocio("Ya hay una caja abierta.")
    monto = parse_decimal(form.get("monto_inicial"), minimo=0, maximo=99_999_999)
    if monto is None:
        raise ErrorNegocio("Ingresá el monto inicial (0 o más).")
    caja = Caja(
        usuario_apertura_id=usuario.id,
        fecha_apertura=ahora(),
        monto_inicial=monto,
        abierta=True,
        observaciones=limpiar(form.get("observaciones"), 255),
    )
    db.session.add(caja)
    try:
        db.session.commit()
    except IntegrityError:  # otra terminal abrió la caja al mismo tiempo
        db.session.rollback()
        raise ErrorNegocio("Ya hay una caja abierta.") from None
    return caja


def registrar_movimiento(caja, tipo, concepto, monto, metodo_id, usuario_id, venta_id=None, gasto_id=None):
    """Agrega un movimiento (sin commit)."""
    mov = MovimientoCaja(
        caja_id=caja.id,
        tipo=tipo,
        concepto=concepto[:150],
        monto=monto,
        metodo_pago_id=metodo_id,
        usuario_id=usuario_id,
        venta_id=venta_id,
        gasto_id=gasto_id,
        fecha=ahora(),
    )
    db.session.add(mov)
    return mov


def movimiento_manual(form, usuario):
    tipo = form.get("tipo")
    if tipo not in TIPOS_MANUALES:
        raise ErrorNegocio("Tipo de movimiento inválido.")
    concepto = limpiar(form.get("concepto"), 150)
    if not concepto:
        raise ErrorNegocio("Indicá el concepto.")
    monto = parse_decimal(form.get("monto"), minimo=0.01, maximo=99_999_999)
    if monto is None:
        raise ErrorNegocio("Ingresá un monto mayor a cero.")
    caja = caja_abierta(bloquear=True)
    if caja is None:
        raise ErrorNegocio("No hay una caja abierta.")
    if tipo in TIPOS_CAJA_SALIDA:
        disponible = resumen(caja)["esperado"]
        if monto > disponible:
            db.session.rollback()
            raise ErrorNegocio(f"No hay suficiente efectivo en caja (disponible ${disponible:.2f}).")
    registrar_movimiento(caja, tipo, concepto, monto, metodo_efectivo().id, usuario.id)
    db.session.commit()


def resumen(caja):
    """Arqueo de una caja: totales por método y tipo, y efectivo esperado."""
    filas = db.session.execute(
        select(MovimientoCaja.tipo, MetodoPago.codigo, MetodoPago.es_efectivo, func.sum(MovimientoCaja.monto))
        .join(MetodoPago, MetodoPago.id == MovimientoCaja.metodo_pago_id)
        .where(MovimientoCaja.caja_id == caja.id)
        .group_by(MovimientoCaja.tipo, MetodoPago.codigo, MetodoPago.es_efectivo)
    ).all()
    cero = Decimal("0")
    ventas = {}
    tipos = {t: cero for t in ("ingreso", "egreso", "retiro", "gasto")}
    anulaciones, anulaciones_efectivo = cero, cero
    efectivo_entradas, efectivo_salidas = cero, cero
    for tipo, codigo, es_efectivo, total in filas:
        total = Decimal(total or 0)
        if tipo == "venta":
            ventas[codigo] = ventas.get(codigo, cero) + total
        elif tipo == "anulacion":
            anulaciones += total
            if es_efectivo:
                anulaciones_efectivo += total
        else:
            tipos[tipo] += total if es_efectivo else cero
        if es_efectivo:
            if tipo in TIPOS_CAJA_SALIDA:
                efectivo_salidas += total
            else:
                efectivo_entradas += total

    cantidad_ventas = db.session.scalar(select(func.count(Venta.id)).where(Venta.caja_id == caja.id)) or 0
    inicial = Decimal(caja.monto_inicial)
    return {
        "inicial": inicial,
        "ventas_efectivo": ventas.get("efectivo", cero),
        "ventas_transferencia": ventas.get("transferencia", cero),
        "ventas_debito": ventas.get("debito", cero),
        "ventas_credito": ventas.get("credito", cero),
        "ventas_tarjeta": ventas.get("debito", cero) + ventas.get("credito", cero),
        "ventas_mercadopago": ventas.get("mercadopago", cero),
        "ventas_otro": ventas.get("otro", cero),
        "ventas_total": sum(ventas.values(), cero),
        "ingresos": tipos["ingreso"],
        "egresos": tipos["egreso"],
        "retiros": tipos["retiro"],
        "gastos": tipos["gasto"],
        "egresos_total": tipos["egreso"] + tipos["retiro"] + tipos["gasto"],
        "anulaciones": anulaciones,
        "anulaciones_efectivo": anulaciones_efectivo,
        "esperado": inicial + efectivo_entradas - efectivo_salidas,
        "cantidad_ventas": cantidad_ventas,
    }


def cerrar(form, usuario):
    caja = caja_abierta(bloquear=True)
    if caja is None:
        raise ErrorNegocio("No hay una caja abierta.")
    declarado = parse_decimal(form.get("monto_declarado"), minimo=0, maximo=99_999_999)
    if declarado is None:
        db.session.rollback()
        raise ErrorNegocio("Ingresá el dinero contado en caja (0 o más).")
    datos = resumen(caja)
    caja.monto_esperado = datos["esperado"]
    caja.monto_declarado = declarado
    caja.diferencia = declarado - datos["esperado"]
    caja.usuario_cierre_id = usuario.id
    caja.fecha_cierre = ahora()
    caja.abierta = None
    obs = limpiar(form.get("observaciones"), 255)
    if obs:
        caja.observaciones = f"{caja.observaciones} | {obs}"[:255] if caja.observaciones else obs
    db.session.commit()
    return caja
