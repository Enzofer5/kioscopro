"""Dashboard principal. Los datos financieros solo se muestran con permiso."""
from datetime import timedelta

from flask import Blueprint, render_template
from flask_login import current_user, login_required

from ..services import caja_service, reporte_service
from ..utils.helpers import hoy

bp = Blueprint("dashboard", __name__)
DIAS = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]


@bp.route("/")
@login_required
def index():
    d = hoy()
    bajo, agotados = reporte_service.conteo_stock()
    ctx = {
        "bajo_stock": bajo,
        "agotados": agotados,
        "alertas": reporte_service.productos_alerta("bajo", limite=6) if current_user.tiene_permiso("stock.ver") else [],
        "mis_ventas": reporte_service.ventas_usuario_hoy(current_user.id),
        "financiero": current_user.tiene_permiso("dashboard.financiero"),
    }
    if ctx["financiero"]:
        inicio_mes = d.replace(day=1)
        caja = caja_service.caja_abierta()
        serie7 = reporte_service.serie_diaria(d - timedelta(days=6), d)
        mensual = reporte_service.ganancias_mensuales(6)
        top = reporte_service.ranking_productos(inicio_mes, d, limite=7)
        metodos = [m for m in reporte_service.ventas_por_metodo(inicio_mes, d) if m["total"] > 0]
        ctx.update(
            hoy_=reporte_service.resumen_ventas(d, d),
            mes=reporte_service.resumen_ventas(inicio_mes, d),
            dinero_caja=caja_service.resumen(caja)["esperado"] if caja else None,
            graficos={
                "ultimos7": {
                    "labels": [f"{DIAS[f['fecha'].weekday()]} {f['fecha'].day}" for f in serie7],
                    "ventas": [float(f["facturacion"]) for f in serie7],
                    "ganancia": [float(f["ganancia_bruta"]) for f in serie7],
                },
                "metodos": {"labels": [m["nombre"] for m in metodos], "valores": [float(m["total"]) for m in metodos]},
                "top": {"labels": [t["producto"].nombre for t in top], "valores": [float(t["cantidad"]) for t in top]},
                "ganancias": {
                    "labels": [g["etiqueta"] for g in mensual],
                    "bruta": [float(g["ganancia_bruta"]) for g in mensual],
                    "gastos": [float(g["gastos"]) for g in mensual],
                    "neta": [float(g["ganancia_neta"]) for g in mensual],
                },
            },
        )
    return render_template("dashboard/index.html", **ctx)
