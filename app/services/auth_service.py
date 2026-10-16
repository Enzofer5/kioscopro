"""Autenticación, registro inicial, recuperación y cambio de contraseña."""
import hashlib
import re
import secrets
from datetime import timedelta

from flask import current_app, url_for
from sqlalchemy import func, or_, select
from werkzeug.security import check_password_hash, generate_password_hash

from ..extensions import db
from ..models import ROL_DUENO, PasswordReset, Rol, Usuario
from ..utils.helpers import ahora, limpiar
from ..utils.mailer import enviar_mail
from . import ErrorNegocio

_HASH_FICTICIO = []


def _hash_ficticio():
    if not _HASH_FICTICIO:
        _HASH_FICTICIO.append(generate_password_hash(secrets.token_hex(8), method="scrypt"))
    return _HASH_FICTICIO[0]


RE_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
RE_USERNAME = re.compile(r"^[a-zA-Z0-9._-]{3,40}$")


def validar_password(password, confirmacion=None):
    if not password or len(password) < 8:
        raise ErrorNegocio("La contraseña debe tener al menos 8 caracteres.")
    if len(password) > 128:
        raise ErrorNegocio("La contraseña es demasiado larga.")
    if not re.search(r"[A-Za-z]", password) or not re.search(r"\d", password):
        raise ErrorNegocio("La contraseña debe combinar letras y números.")
    if confirmacion is not None and password != confirmacion:
        raise ErrorNegocio("Las contraseñas no coinciden.")


def validar_email(email):
    email = (limpiar(email, 120) or "").lower()
    if not RE_EMAIL.match(email):
        raise ErrorNegocio("Ingresá un email válido.")
    return email


def validar_username(username):
    username = (username or "").strip().lower()
    if not RE_USERNAME.match(username):
        raise ErrorNegocio("El usuario debe tener 3 a 40 caracteres: letras, números, punto, guion o guion bajo.")
    return username


def hay_usuarios():
    return db.session.scalar(select(func.count(Usuario.id))) > 0


def autenticar(identificador, password):
    """Devuelve el usuario si las credenciales son correctas y está activo."""
    ident = (identificador or "").strip().lower()
    if not ident or not password:
        return None
    usuario = db.session.scalar(
        select(Usuario).where(or_(func.lower(Usuario.username) == ident, func.lower(Usuario.email) == ident))
    )
    if usuario is None:
        # Igualamos el tiempo de respuesta para no revelar si el usuario existe
        check_password_hash(_hash_ficticio(), password)
        return None
    if not usuario.check_password(password):
        return None
    if not usuario.activo:
        raise ErrorNegocio("Tu usuario está desactivado. Consultá con el administrador.")
    usuario.ultimo_acceso = ahora()
    db.session.commit()
    return usuario


def registrar_dueno(form):
    if hay_usuarios():
        raise ErrorNegocio("El sistema ya fue inicializado.")
    nombre = limpiar(form.get("nombre"), 80)
    apellido = limpiar(form.get("apellido"), 80)
    if not nombre or not apellido:
        raise ErrorNegocio("Completá nombre y apellido.")
    username = validar_username(form.get("username"))
    email = validar_email(form.get("email"))
    validar_password(form.get("password"), form.get("password2"))
    rol = db.session.scalar(select(Rol).where(Rol.nombre == ROL_DUENO))
    if rol is None:
        raise ErrorNegocio("Faltan los datos base. Ejecutá 'flask init-db'.")
    usuario = Usuario(
        username=username, email=email, nombre=nombre, apellido=apellido, rol=rol, activo=True, creado_en=ahora()
    )
    usuario.set_password(form.get("password"))
    db.session.add(usuario)
    db.session.commit()
    return usuario


def _hash_token(token):
    return hashlib.sha256(token.encode()).hexdigest()


def solicitar_recuperacion(email):
    """Genera un token de un solo uso (válido 1 hora) y lo envía por email.
    Siempre responde igual para no revelar qué emails existen."""
    email = (email or "").strip().lower()
    usuario = db.session.scalar(select(Usuario).where(func.lower(Usuario.email) == email))
    if usuario is None or not usuario.activo:
        return
    token = secrets.token_urlsafe(32)
    db.session.add(
        PasswordReset(
            usuario_id=usuario.id,
            token_hash=_hash_token(token),
            expira_en=ahora() + timedelta(hours=1),
            creado_en=ahora(),
        )
    )
    db.session.commit()
    base = current_app.config.get("APP_URL")
    enlace = (base + url_for("auth.restablecer", token=token)) if base else url_for("auth.restablecer", token=token, _external=True)
    enviar_mail(
        usuario.email,
        f"{current_app.config['NEGOCIO_NOMBRE']} - Recuperar contraseña",
        f"Hola {usuario.nombre}:\n\nPara crear una nueva contraseña ingresá a este enlace (válido por 1 hora):\n{enlace}\n\n"
        "Si no lo pediste, ignorá este mensaje.",
    )


def token_valido(token):
    if not token:
        return None
    registro = db.session.scalar(select(PasswordReset).where(PasswordReset.token_hash == _hash_token(token)))
    if registro is None or registro.usado_en is not None or registro.expira_en < ahora():
        return None
    return registro


def restablecer_password(token, password, confirmacion):
    registro = token_valido(token)
    if registro is None:
        raise ErrorNegocio("El enlace no es válido o ya venció. Pedí uno nuevo.")
    validar_password(password, confirmacion)
    registro.usuario.set_password(password)
    registro.usuario.debe_cambiar_password = False
    registro.usado_en = ahora()
    db.session.commit()


def cambiar_password(usuario, actual, nueva, confirmacion):
    if not usuario.check_password(actual or ""):
        raise ErrorNegocio("La contraseña actual no es correcta.")
    validar_password(nueva, confirmacion)
    if usuario.check_password(nueva):
        raise ErrorNegocio("La nueva contraseña debe ser distinta de la actual.")
    usuario.set_password(nueva)
    usuario.debe_cambiar_password = False
    db.session.commit()
