"""Alta/modificación y consultas de clientes, proveedores y empleados."""
import re

from sqlalchemy import func, or_, select

from ..extensions import db
from ..models import ESTADO_COMPLETADA, Cliente, Compra, Empleado, Proveedor, Venta
from ..utils.helpers import ahora, hoy, limpiar, parse_fecha
from . import ErrorNegocio
from .auth_service import RE_EMAIL


def _email_opcional(valor):
    email = (limpiar(valor, 120) or "").lower() or None
    if email and not RE_EMAIL.match(email):
        raise ErrorNegocio("El email no es válido.")
    return email


def _dni(valor, obligatorio=False):
    dni = re.sub(r"\D", "", valor or "")
    if not dni:
        if obligatorio:
            raise ErrorNegocio("El DNI es obligatorio.")
        return None
    if not 6 <= len(dni) <= 11:
        raise ErrorNegocio("El DNI no es válido.")
    return dni


def _telefono(valor):
    tel = limpiar(valor, 30)
    if tel and not re.fullmatch(r"[0-9+()\-\s]{6,30}", tel):
        raise ErrorNegocio("El teléfono solo puede contener números, espacios, +, - y paréntesis.")
    return tel


def validar_cuit(valor):
    """Valida CUIT/CUIL argentino (11 dígitos con dígito verificador)."""
    cuit = re.sub(r"\D", "", valor or "")
    if not cuit:
        return None
    if len(cuit) != 11:
        raise ErrorNegocio("El CUIT debe tener 11 dígitos.")
    pesos = [5, 4, 3, 2, 7, 6, 5, 4, 3, 2]
    suma = sum(int(cuit[i]) * pesos[i] for i in range(10))
    verificador = 11 - (suma % 11)
    verificador = 0 if verificador == 11 else 9 if verificador == 10 else verificador
    if verificador != int(cuit[10]):
        raise ErrorNegocio("El CUIT no es válido (dígito verificador incorrecto).")
    return f"{cuit[:2]}-{cuit[2:10]}-{cuit[10]}"


# ----------------------------------------------------------------- Clientes


def guardar_cliente(form, cliente=None):
    nombre = limpiar(form.get("nombre"), 80)
    apellido = limpiar(form.get("apellido"), 80)
    if not nombre or not apellido:
        raise ErrorNegocio("Completá nombre y apellido.")
    dni = _dni(form.get("dni"))
    if dni:
        q = select(Cliente.id).where(Cliente.dni == dni)
        if cliente:
            q = q.where(Cliente.id != cliente.id)
        if db.session.scalar(q):
            raise ErrorNegocio("Ya existe un cliente con ese DNI.")
    if cliente is None:
        cliente = Cliente(fecha_registro=ahora(), activo=True)
        db.session.add(cliente)
    cliente.nombre, cliente.apellido, cliente.dni = nombre, apellido, dni
    cliente.telefono = _telefono(form.get("telefono"))
    cliente.email = _email_opcional(form.get("email"))
    cliente.direccion = limpiar(form.get("direccion"), 200)
    db.session.commit()
    return cliente


def buscar_clientes(texto, estado=None):
    q = select(Cliente)
    if texto:
        like = f"%{texto.strip()}%"
        q = q.where(or_(Cliente.nombre.ilike(like), Cliente.apellido.ilike(like), Cliente.dni.ilike(like),
                        Cliente.telefono.ilike(like), Cliente.email.ilike(like)))
    if estado == "activos":
        q = q.where(Cliente.activo.is_(True))
    elif estado == "inactivos":
        q = q.where(Cliente.activo.is_(False))
    return q.order_by(Cliente.apellido, Cliente.nombre)


def estadisticas_cliente(cliente_id):
    fila = db.session.execute(
        select(func.count(Venta.id), func.coalesce(func.sum(Venta.total), 0), func.max(Venta.fecha)).where(
            Venta.cliente_id == cliente_id, Venta.estado == ESTADO_COMPLETADA
        )
    ).one()
    return {"cantidad": fila[0], "total": fila[1], "ultima": fila[2]}


# ----------------------------------------------------------------- Proveedores


def guardar_proveedor(form, proveedor=None):
    razon = limpiar(form.get("razon_social"), 150)
    if not razon:
        raise ErrorNegocio("La razón social es obligatoria.")
    cuit = validar_cuit(form.get("cuit"))
    if cuit:
        q = select(Proveedor.id).where(Proveedor.cuit == cuit)
        if proveedor:
            q = q.where(Proveedor.id != proveedor.id)
        if db.session.scalar(q):
            raise ErrorNegocio("Ya existe un proveedor con ese CUIT.")
    if proveedor is None:
        proveedor = Proveedor(creado_en=ahora(), activo=True)
        db.session.add(proveedor)
    proveedor.razon_social, proveedor.cuit = razon, cuit
    proveedor.telefono = _telefono(form.get("telefono"))
    proveedor.email = _email_opcional(form.get("email"))
    proveedor.direccion = limpiar(form.get("direccion"), 200)
    proveedor.contacto = limpiar(form.get("contacto"), 100)
    obs = (form.get("observaciones") or "").strip()
    proveedor.observaciones = obs[:2000] or None
    db.session.commit()
    return proveedor


def estadisticas_proveedor(proveedor_id):
    fila = db.session.execute(
        select(func.count(Compra.id), func.coalesce(func.sum(Compra.total), 0), func.max(Compra.fecha)).where(
            Compra.proveedor_id == proveedor_id
        )
    ).one()
    return {"cantidad": fila[0], "total": fila[1], "ultima": fila[2]}


# ----------------------------------------------------------------- Empleados


def guardar_empleado(form, empleado=None):
    nombre = limpiar(form.get("nombre"), 80)
    apellido = limpiar(form.get("apellido"), 80)
    puesto = limpiar(form.get("puesto"), 60)
    if not nombre or not apellido or not puesto:
        raise ErrorNegocio("Completá nombre, apellido y puesto.")
    dni = _dni(form.get("dni"), obligatorio=True)
    q = select(Empleado.id).where(Empleado.dni == dni)
    if empleado:
        q = q.where(Empleado.id != empleado.id)
    if db.session.scalar(q):
        raise ErrorNegocio("Ya existe un empleado con ese DNI.")
    fecha = parse_fecha(form.get("fecha_ingreso"))
    if fecha is None:
        raise ErrorNegocio("Ingresá la fecha de ingreso.")
    if fecha > hoy():
        raise ErrorNegocio("La fecha de ingreso no puede ser futura.")
    if empleado is None:
        empleado = Empleado(creado_en=ahora(), activo=True)
        db.session.add(empleado)
    empleado.nombre, empleado.apellido, empleado.dni, empleado.puesto = nombre, apellido, dni, puesto
    empleado.telefono = _telefono(form.get("telefono"))
    empleado.email = _email_opcional(form.get("email"))
    empleado.fecha_ingreso = fecha
    db.session.commit()
    return empleado
