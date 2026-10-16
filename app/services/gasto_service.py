"""Gastos del negocio. Si se pagan en efectivo desde la caja, generan un egreso de caja."""
from sqlalchemy import select

from ..extensions import db
from ..models import CategoriaGasto, Gasto, MetodoPago, MovimientoCaja
from ..utils.helpers import ahora, hoy, limpiar, parse_decimal, parse_fecha, parse_int
from . import ErrorNegocio
from . import caja_service


def registrar(form, usuario):
    try:
        categoria = db.session.get(CategoriaGasto, parse_int(form.get("categoria_id"), 0))
        if categoria is None:
            raise ErrorNegocio("Seleccioná una categoría.")
        descripcion = limpiar(form.get("descripcion"), 200)
        if not descripcion:
            raise ErrorNegocio("Ingresá una descripción.")
        monto = parse_decimal(form.get("monto"), minimo=0.01, maximo=99_999_999)
        if monto is None:
            raise ErrorNegocio("Ingresá un monto mayor a cero.")
        metodo = db.session.get(MetodoPago, parse_int(form.get("metodo_pago_id"), 0))
        if metodo is None:
            raise ErrorNegocio("Seleccioná el método de pago.")
        fecha = parse_fecha(form.get("fecha"), hoy())
        if fecha > hoy():
            raise ErrorNegocio("La fecha no puede ser futura.")

        gasto = Gasto(
            categoria_id=categoria.id, descripcion=descripcion, monto=monto, metodo_pago_id=metodo.id,
            fecha=fecha, usuario_id=usuario.id, creado_en=ahora(),
        )
        db.session.add(gasto)
        db.session.flush()

        if metodo.es_efectivo and form.get("desde_caja"):
            caja = caja_service.caja_abierta(bloquear=True)
            if caja is None:
                raise ErrorNegocio("No hay caja abierta para sacar el dinero. Destildá «Sale de la caja».")
            if monto > caja_service.resumen(caja)["esperado"]:
                raise ErrorNegocio("No hay suficiente efectivo en la caja.")
            caja_service.registrar_movimiento(
                caja, "gasto", f"Gasto: {categoria.nombre} - {descripcion}", monto, metodo.id, usuario.id, gasto_id=gasto.id
            )
        db.session.commit()
        return gasto
    except Exception:
        db.session.rollback()
        raise


def eliminar(gasto):
    if db.session.scalar(select(MovimientoCaja.id).where(MovimientoCaja.gasto_id == gasto.id)):
        raise ErrorNegocio("Este gasto salió de la caja y quedó en su arqueo; no se puede eliminar. "
                           "Registrá un ingreso manual en caja si fue un error.")
    db.session.delete(gasto)
    db.session.commit()
