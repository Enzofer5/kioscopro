"""Consultas de reportes y dashboard.

Ganancia bruta = ventas netas (total cobrado) - costo de lo vendido
(el costo es el precio de compra congelado en cada línea de venta).
Ganancia neta  = ganancia bruta - gastos del período.
Solo se consideran ventas en estado 'completada'.
"""
from collections import OrderedDict
from datetime import timedelta
from decimal import Decimal

from sqlalchemy import func, select

from ..extensions import db
from ..models import (
    ESTADO_COMPLETADA,
    CategoriaGasto,
    DetalleVenta,
    Gasto,
    MetodoPago,
    Pago,
    Producto,
    Venta,
)
from ..utils.helpers import a_fecha, fin_dia, hoy, inicio_dia

CERO = Decimal("0")


def _d(valor):
    return Decimal(str(valor)) if valor is not None else CERO


def _filtro_ventas(desde, hasta):
    return (Venta.estado == ESTADO_COMPLETADA, Venta.fecha >= inicio_dia(desde), Venta.fecha < fin_dia(hasta))


def resumen_ventas(desde, hasta):
    cantidad, facturacion, descuentos = db.session.execute(
        select(func.count(Venta.id), func.sum(Venta.total), func.sum(Venta.descuento)).where(*_filtro_ventas(desde, hasta))
    ).one()
    costo = db.session.scalar(
        select(func.sum(DetalleVenta.cantidad * DetalleVenta.costo_unitario))
        .join(Venta, Venta.id == DetalleVenta.venta_id)
        .where(*_filtro_ventas(desde, hasta))
    )
    gastos = total_gastos(desde, hasta)
    facturacion, costo = _d(facturacion), _d(costo)
    bruta = facturacion - costo
    return {
        "cantidad": cantidad or 0,
        "facturacion": facturacion,
        "costo": costo,
        "descuentos": _d(descuentos),
        "ganancia_bruta": bruta,
        "gastos": gastos,
        "ganancia_neta": bruta - gastos,
        "ticket_promedio": (facturacion / cantidad) if cantidad else CERO,
        "margen_pct": (bruta / facturacion * 100) if facturacion else CERO,
    }


def total_gastos(desde, hasta):
    return _d(db.session.scalar(select(func.sum(Gasto.monto)).where(Gasto.fecha >= desde, Gasto.fecha <= hasta)))


def serie_diaria(desde, hasta):
    """Por cada día del rango: facturación, costo, ganancia bruta, gastos, neta y cantidad."""
    dia_col = func.date(Venta.fecha)
    ventas = db.session.execute(
        select(dia_col, func.count(Venta.id), func.sum(Venta.total)).where(*_filtro_ventas(desde, hasta)).group_by(dia_col)
    ).all()
    costos = db.session.execute(
        select(dia_col, func.sum(DetalleVenta.cantidad * DetalleVenta.costo_unitario))
        .join(Venta, Venta.id == DetalleVenta.venta_id)
        .where(*_filtro_ventas(desde, hasta))
        .group_by(dia_col)
    ).all()
    gastos = db.session.execute(
        select(Gasto.fecha, func.sum(Gasto.monto)).where(Gasto.fecha >= desde, Gasto.fecha <= hasta).group_by(Gasto.fecha)
    ).all()
    serie = OrderedDict()
    d = desde
    while d <= hasta:
        serie[d] = {"fecha": d, "cantidad": 0, "facturacion": CERO, "costo": CERO, "gastos": CERO}
        d += timedelta(days=1)
    for dia, cant, total in ventas:
        f = a_fecha(dia)
        if f in serie:
            serie[f]["cantidad"], serie[f]["facturacion"] = cant, _d(total)
    for dia, costo in costos:
        f = a_fecha(dia)
        if f in serie:
            serie[f]["costo"] = _d(costo)
    for dia, monto in gastos:
        f = a_fecha(dia)
        if f in serie:
            serie[f]["gastos"] = _d(monto)
    for fila in serie.values():
        fila["ganancia_bruta"] = fila["facturacion"] - fila["costo"]
        fila["ganancia_neta"] = fila["ganancia_bruta"] - fila["gastos"]
    return list(serie.values())


def agrupar_serie(serie, agrupacion):
    """Agrupa la serie diaria por 'dia', 'semana' (ISO, lunes a domingo) o 'mes'."""
    if agrupacion == "dia":
        for fila in serie:
            fila["etiqueta"] = fila["fecha"].strftime("%d/%m")
        return serie
    grupos = OrderedDict()
    for fila in serie:
        f = fila["fecha"]
        if agrupacion == "semana":
            inicio = f - timedelta(days=f.weekday())
            clave, etiqueta = inicio, f"Sem. {inicio.strftime('%d/%m')}"
        else:
            clave, etiqueta = (f.year, f.month), f.strftime("%m/%Y")
        g = grupos.setdefault(clave, {"etiqueta": etiqueta, "cantidad": 0, "facturacion": CERO, "costo": CERO,
                                      "gastos": CERO, "ganancia_bruta": CERO, "ganancia_neta": CERO})
        for k in ("cantidad", "facturacion", "costo", "gastos", "ganancia_bruta", "ganancia_neta"):
            g[k] += fila[k]
    return list(grupos.values())


def ventas_por_metodo(desde, hasta):
    filas = db.session.execute(
        select(MetodoPago.nombre, MetodoPago.codigo, func.count(Pago.id), func.sum(Pago.monto))
        .join(Pago, Pago.metodo_pago_id == MetodoPago.id)
        .join(Venta, Venta.id == Pago.venta_id)
        .where(*_filtro_ventas(desde, hasta))
        .group_by(MetodoPago.nombre, MetodoPago.codigo, MetodoPago.orden)
        .order_by(MetodoPago.orden)
    ).all()
    por_codigo = {c: {"nombre": n, "codigo": c, "cantidad": q, "total": _d(t)} for n, c, q, t in filas}
    # Incluye los métodos sin movimientos (con 0) para que el reporte sea completo
    todos = db.session.execute(select(MetodoPago.nombre, MetodoPago.codigo).order_by(MetodoPago.orden)).all()
    return [por_codigo.get(c, {"nombre": n, "codigo": c, "cantidad": 0, "total": CERO}) for n, c in todos]


def ranking_productos(desde, hasta, orden="mas", criterio="cantidad", limite=10):
    """Ranking de productos del período.
    orden='mas' -> más vendidos; orden='menos' -> menos vendidos (incluye productos activos sin ventas)."""
    sub = (
        select(
            DetalleVenta.producto_id.label("pid"),
            func.sum(DetalleVenta.cantidad).label("cantidad"),
            func.sum(DetalleVenta.subtotal).label("facturacion"),
            func.sum(DetalleVenta.subtotal - DetalleVenta.cantidad * DetalleVenta.costo_unitario).label("ganancia"),
        )
        .join(Venta, Venta.id == DetalleVenta.venta_id)
        .where(*_filtro_ventas(desde, hasta))
        .group_by(DetalleVenta.producto_id)
        .subquery()
    )
    cantidad = func.coalesce(sub.c.cantidad, 0)
    facturacion = func.coalesce(sub.c.facturacion, 0)
    ganancia = func.coalesce(sub.c.ganancia, 0)
    columna = facturacion if criterio == "facturacion" else cantidad
    q = select(Producto, cantidad, facturacion, ganancia)
    if orden == "menos":
        q = q.outerjoin(sub, sub.c.pid == Producto.id).where(Producto.activo.is_(True)).order_by(columna.asc(), Producto.nombre)
    else:
        q = q.join(sub, sub.c.pid == Producto.id).order_by(columna.desc(), Producto.nombre)
    return [
        {"producto": p, "cantidad": _d(c), "facturacion": _d(f), "ganancia": _d(g)}
        for p, c, f, g in db.session.execute(q.limit(limite)).all()
    ]


def gastos_por_categoria(desde, hasta):
    return [
        {"categoria": n, "total": _d(t)}
        for n, t in db.session.execute(
            select(CategoriaGasto.nombre, func.sum(Gasto.monto))
            .join(Gasto, Gasto.categoria_id == CategoriaGasto.id)
            .where(Gasto.fecha >= desde, Gasto.fecha <= hasta)
            .group_by(CategoriaGasto.nombre)
            .order_by(func.sum(Gasto.monto).desc())
        ).all()
    ]


def conteo_stock():
    bajo = db.session.scalar(
        select(func.count(Producto.id)).where(
            Producto.activo.is_(True), Producto.stock_actual > 0, Producto.stock_actual <= Producto.stock_minimo
        )
    )
    agotados = db.session.scalar(
        select(func.count(Producto.id)).where(Producto.activo.is_(True), Producto.stock_actual <= 0)
    )
    return bajo or 0, agotados or 0


def productos_alerta(tipo, limite=None):
    q = select(Producto).where(Producto.activo.is_(True))
    if tipo == "agotados":
        q = q.where(Producto.stock_actual <= 0).order_by(Producto.nombre)
    else:
        q = q.where(Producto.stock_actual > 0, Producto.stock_actual <= Producto.stock_minimo).order_by(
            (Producto.stock_actual - Producto.stock_minimo).asc(), Producto.nombre
        )
    if limite:
        q = q.limit(limite)
    return db.session.scalars(q).all()


def ganancias_mensuales(meses=6):
    """Últimos N meses (incluido el actual) con ganancia bruta, gastos y neta."""
    fin = hoy()
    inicio = fin.replace(day=1)
    for _ in range(meses - 1):
        inicio = (inicio - timedelta(days=1)).replace(day=1)
    return agrupar_serie(serie_diaria(inicio, fin), "mes")


def ventas_usuario_hoy(usuario_id):
    d = hoy()
    cantidad, total = db.session.execute(
        select(func.count(Venta.id), func.sum(Venta.total)).where(*_filtro_ventas(d, d), Venta.usuario_id == usuario_id)
    ).one()
    return cantidad or 0, _d(total)
