"""Reportes de ventas, productos, ganancias y métodos de pago."""
from flask import Blueprint, render_template, request

from ..services import reporte_service
from ..utils.decorators import permiso_requerido
from ..utils.helpers import rango_periodo

bp = Blueprint("reportes", __name__, url_prefix="/reportes")

PERIODOS = [("hoy", "Hoy"), ("ayer", "Ayer"), ("7dias", "Últimos 7 días"), ("mes", "Este mes"),
            ("mes_anterior", "Mes anterior"), ("rango", "Rango de fechas")]


def _periodo(defecto="mes"):
    periodo = request.args.get("periodo", defecto)
    if periodo not in dict(PERIODOS):
        periodo = defecto
    desde, hasta, etiqueta = rango_periodo(periodo, request.args.get("desde"), request.args.get("hasta"))
    return {"periodo": periodo, "desde": desde, "hasta": hasta, "etiqueta": etiqueta, "periodos": PERIODOS}


@bp.route("/")
@bp.route("/ventas")
@permiso_requerido("reportes.ver")
def ventas():
    p = _periodo("hoy")
    resumen = reporte_service.resumen_ventas(p["desde"], p["hasta"])
    serie = reporte_service.serie_diaria(p["desde"], p["hasta"])
    grafico = {
        "labels": [f["fecha"].strftime("%d/%m") for f in serie],
        "ventas": [float(f["facturacion"]) for f in serie],
        "cantidad": [f["cantidad"] for f in serie],
    }
    return render_template("reportes/ventas.html", p=p, resumen=resumen, serie=serie, grafico=grafico, seccion="ventas")


@bp.route("/productos")
@permiso_requerido("reportes.ver")
def productos():
    p = _periodo("mes")
    mas = reporte_service.ranking_productos(p["desde"], p["hasta"], "mas", "cantidad", 15)
    return render_template(
        "reportes/productos.html", p=p, seccion="productos",
        mas_vendidos=mas,
        menos_vendidos=reporte_service.ranking_productos(p["desde"], p["hasta"], "menos", "cantidad", 15),
        mayor_facturacion=reporte_service.ranking_productos(p["desde"], p["hasta"], "mas", "facturacion", 15),
        bajo_stock=reporte_service.productos_alerta("bajo", 50),
        agotados=reporte_service.productos_alerta("agotados", 50),
        grafico={"labels": [m["producto"].nombre for m in mas[:10]], "valores": [float(m["cantidad"]) for m in mas[:10]]},
    )


@bp.route("/ganancias")
@permiso_requerido("reportes.ver")
def ganancias():
    p = _periodo("mes")
    agrupacion = request.args.get("agrupacion", "dia")
    if agrupacion not in ("dia", "semana", "mes"):
        agrupacion = "dia"
    filas = reporte_service.agrupar_serie(reporte_service.serie_diaria(p["desde"], p["hasta"]), agrupacion)
    resumen = reporte_service.resumen_ventas(p["desde"], p["hasta"])
    grafico = {
        "labels": [f["etiqueta"] for f in filas],
        "bruta": [float(f["ganancia_bruta"]) for f in filas],
        "gastos": [float(f["gastos"]) for f in filas],
        "neta": [float(f["ganancia_neta"]) for f in filas],
    }
    return render_template("reportes/ganancias.html", p=p, seccion="ganancias", filas=filas, resumen=resumen,
                           agrupacion=agrupacion, grafico=grafico,
                           gastos_cat=reporte_service.gastos_por_categoria(p["desde"], p["hasta"]))


@bp.route("/pagos")
@permiso_requerido("reportes.ver")
def pagos():
    p = _periodo("mes")
    metodos = reporte_service.ventas_por_metodo(p["desde"], p["hasta"])
    total = sum((m["total"] for m in metodos), 0)
    grafico = {"labels": [m["nombre"] for m in metodos], "valores": [float(m["total"]) for m in metodos]}
    return render_template("reportes/pagos.html", p=p, seccion="pagos", metodos=metodos, total=total, grafico=grafico)
