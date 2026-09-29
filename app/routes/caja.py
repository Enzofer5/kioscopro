"""Caja: apertura, movimientos, cierre e historial de cierres."""
from datetime import timedelta

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user
from sqlalchemy import select

from ..extensions import db
from ..models import Caja, MovimientoCaja
from ..services import ErrorNegocio, caja_service
from ..utils.decorators import permiso_requerido
from ..utils.helpers import fin_dia, hoy, inicio_dia, parse_fecha, parse_int

bp = Blueprint("caja", __name__, url_prefix="/caja")


@bp.route("/")
@permiso_requerido("caja.operar")
def index():
    caja = caja_service.caja_abierta()
    if caja is None:
        ultima = db.session.scalar(select(Caja).where(Caja.abierta.is_(None)).order_by(Caja.fecha_cierre.desc()).limit(1))
        return render_template("caja/apertura.html", ultima=ultima)
    movimientos = caja.movimientos.order_by(MovimientoCaja.id.desc()).limit(200).all()
    return render_template("caja/index.html", caja=caja, resumen=caja_service.resumen(caja),
                           movimientos=movimientos, tipos=caja_service.TIPOS_MANUALES)


@bp.route("/abrir", methods=["POST"])
@permiso_requerido("caja.operar")
def abrir():
    try:
        caja_service.abrir(request.form, current_user)
        flash("Caja abierta. ¡Buenas ventas!", "success")
    except ErrorNegocio as exc:
        flash(str(exc), "danger")
    return redirect(url_for("caja.index"))


@bp.route("/movimiento", methods=["POST"])
@permiso_requerido("caja.operar")
def movimiento():
    try:
        caja_service.movimiento_manual(request.form, current_user)
        flash("Movimiento registrado.", "success")
    except ErrorNegocio as exc:
        flash(str(exc), "danger")
    return redirect(url_for("caja.index"))


@bp.route("/cerrar", methods=["GET", "POST"])
@permiso_requerido("caja.operar")
def cerrar():
    caja = caja_service.caja_abierta()
    if caja is None:
        flash("No hay una caja abierta.", "warning")
        return redirect(url_for("caja.index"))
    if request.method == "POST":
        try:
            cerrada = caja_service.cerrar(request.form, current_user)
            flash("Caja cerrada correctamente.", "success")
            return redirect(url_for("caja.detalle", caja_id=cerrada.id))
        except ErrorNegocio as exc:
            flash(str(exc), "danger")
    return render_template("caja/cierre.html", caja=caja, resumen=caja_service.resumen(caja))


@bp.route("/historial")
@permiso_requerido("caja.historial")
def historial():
    desde = parse_fecha(request.args.get("desde"), hoy() - timedelta(days=30))
    hasta = parse_fecha(request.args.get("hasta"), hoy())
    q = select(Caja).where(Caja.fecha_apertura >= inicio_dia(desde), Caja.fecha_apertura < fin_dia(hasta))
    if parse_int(request.args.get("usuario_id")):
        q = q.where(Caja.usuario_apertura_id == parse_int(request.args.get("usuario_id")))
    paginacion = db.paginate(q.order_by(Caja.id.desc()), page=parse_int(request.args.get("page"), 1),
                             per_page=20, error_out=False)
    return render_template("caja/historial.html", paginacion=paginacion, desde=desde, hasta=hasta)


@bp.route("/<int:caja_id>")
@permiso_requerido("caja.historial", "caja.operar")
def detalle(caja_id):
    caja = db.get_or_404(Caja, caja_id)
    # Sin permiso de historial solo se puede ver el cierre propio
    if not current_user.tiene_permiso("caja.historial") and current_user.id not in (caja.usuario_apertura_id, caja.usuario_cierre_id):
        abort(403)
    movimientos = caja.movimientos.order_by(MovimientoCaja.id).all()
    return render_template("caja/detalle.html", caja=caja, resumen=caja_service.resumen(caja), movimientos=movimientos)
