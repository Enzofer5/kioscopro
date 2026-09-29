"""Gestión de usuarios con reglas de jerarquía de roles."""
import secrets
import string

from sqlalchemy import func, select

from ..extensions import db
from ..models import ROL_DUENO, Empleado, Rol, Usuario
from ..utils.helpers import ahora, limpiar, parse_int
from . import ErrorNegocio
from .auth_service import validar_email, validar_password, validar_username


def roles_asignables(actor):
    """El dueño puede asignar cualquier rol; el resto no puede crear dueños."""
    roles = db.session.scalars(select(Rol).order_by(Rol.id)).all()
    return roles if actor.es_dueno else [r for r in roles if r.nombre != ROL_DUENO]


def puede_editar(actor, usuario):
    if usuario.es_dueno and not actor.es_dueno:
        return False
    return True


def _duenos_activos(excluir_id=None):
    q = select(func.count(Usuario.id)).join(Rol).where(Rol.nombre == ROL_DUENO, Usuario.activo.is_(True))
    if excluir_id:
        q = q.where(Usuario.id != excluir_id)
    return db.session.scalar(q)


def guardar(actor, form, usuario=None):
    nuevo = usuario is None
    if not nuevo and not puede_editar(actor, usuario):
        raise ErrorNegocio("No podés modificar la cuenta del dueño.")

    nombre = limpiar(form.get("nombre"), 80)
    apellido = limpiar(form.get("apellido"), 80)
    if not nombre or not apellido:
        raise ErrorNegocio("Completá nombre y apellido.")
    username = validar_username(form.get("username"))
    email = validar_email(form.get("email"))

    rol = db.session.get(Rol, parse_int(form.get("rol_id"), 0))
    if rol is None or rol not in roles_asignables(actor):
        raise ErrorNegocio("Seleccioná un rol válido.")

    empleado = None
    empleado_id = parse_int(form.get("empleado_id"))
    if empleado_id:
        empleado = db.session.get(Empleado, empleado_id)
        if empleado is None:
            raise ErrorNegocio("El empleado seleccionado no existe.")
        if empleado.usuario and (nuevo or empleado.usuario.id != usuario.id):
            raise ErrorNegocio("Ese empleado ya tiene un usuario asignado.")

    dup = select(Usuario).where((func.lower(Usuario.username) == username) | (func.lower(Usuario.email) == email))
    if not nuevo:
        dup = dup.where(Usuario.id != usuario.id)
    if db.session.scalar(dup):
        raise ErrorNegocio("Ya existe un usuario con ese nombre de usuario o email.")

    if not nuevo and usuario.es_dueno and rol.nombre != ROL_DUENO and _duenos_activos(excluir_id=usuario.id) == 0:
        raise ErrorNegocio("Debe existir al menos un dueño activo.")

    if nuevo:
        validar_password(form.get("password"), form.get("password2"))
        usuario = Usuario(creado_en=ahora(), activo=True)
        usuario.set_password(form.get("password"))
        usuario.debe_cambiar_password = True
        db.session.add(usuario)

    usuario.nombre, usuario.apellido = nombre, apellido
    usuario.username, usuario.email = username, email
    usuario.rol = rol
    usuario.empleado = empleado
    db.session.commit()
    return usuario


def cambiar_estado(actor, usuario):
    if usuario.id == actor.id:
        raise ErrorNegocio("No podés desactivar tu propio usuario.")
    if not puede_editar(actor, usuario):
        raise ErrorNegocio("No podés modificar la cuenta del dueño.")
    if usuario.activo and usuario.es_dueno and _duenos_activos(excluir_id=usuario.id) == 0:
        raise ErrorNegocio("Debe existir al menos un dueño activo.")
    usuario.activo = not usuario.activo
    usuario.version_sesion += 1  # cierra sus sesiones abiertas
    db.session.commit()
    return usuario.activo


def resetear_password(actor, usuario):
    """Genera una contraseña temporal que el usuario deberá cambiar al ingresar."""
    if not puede_editar(actor, usuario):
        raise ErrorNegocio("No podés modificar la cuenta del dueño.")
    alfabeto = string.ascii_letters + string.digits
    while True:
        temporal = "".join(secrets.choice(alfabeto) for _ in range(10))
        if any(c.isdigit() for c in temporal) and any(c.isalpha() for c in temporal):
            break
    usuario.set_password(temporal)
    usuario.debe_cambiar_password = True
    db.session.commit()
    return temporal


def actualizar_perfil(usuario, form):
    nombre = limpiar(form.get("nombre"), 80)
    apellido = limpiar(form.get("apellido"), 80)
    if not nombre or not apellido:
        raise ErrorNegocio("Completá nombre y apellido.")
    email = validar_email(form.get("email"))
    if db.session.scalar(select(Usuario).where(func.lower(Usuario.email) == email, Usuario.id != usuario.id)):
        raise ErrorNegocio("Ese email ya está en uso.")
    usuario.nombre, usuario.apellido, usuario.email = nombre, apellido, email
    db.session.commit()
