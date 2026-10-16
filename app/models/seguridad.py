"""Usuarios, roles, permisos y tokens de recuperación de contraseña."""
from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from ..extensions import db

# ---------------------------------------------------------------------------
# Catálogo de permisos y su asignación por rol (fuente única de verdad;
# database/schema.sql inserta exactamente los mismos datos).
# ---------------------------------------------------------------------------
PERMISOS = {
    "dashboard.financiero": "Ver montos, ganancias y caja en el dashboard",
    "ventas.crear": "Usar el punto de venta",
    "ventas.historial": "Consultar historial de ventas",
    "ventas.anular": "Anular ventas y registrar devoluciones",
    "productos.ver": "Consultar productos y precios",
    "productos.gestionar": "Alta, baja y modificación de productos, categorías y marcas",
    "stock.ver": "Ver stock y alertas",
    "stock.ajustar": "Registrar entradas, salidas y ajustes de stock",
    "compras.gestionar": "Registrar y consultar compras",
    "proveedores.gestionar": "Administrar proveedores",
    "clientes.ver": "Consultar clientes",
    "clientes.gestionar": "Alta y modificación de clientes",
    "caja.operar": "Abrir, registrar movimientos y cerrar caja",
    "caja.historial": "Consultar cierres de caja anteriores",
    "gastos.gestionar": "Registrar y consultar gastos",
    "empleados.gestionar": "Administrar empleados",
    "usuarios.gestionar": "Administrar usuarios y roles",
    "reportes.ver": "Ver reportes",
}

ROL_DUENO = "Dueño"
ROL_ADMIN = "Administrador"
ROL_VENDEDOR = "Vendedor"
ROL_CAJERO = "Cajero"

ROLES = {
    ROL_DUENO: ("Acceso total al sistema", list(PERMISOS)),
    ROL_ADMIN: ("Gestión completa del negocio (no puede modificar al dueño)", list(PERMISOS)),
    ROL_VENDEDOR: (
        "Atiende el mostrador",
        ["ventas.crear", "productos.ver", "stock.ver", "clientes.ver", "clientes.gestionar"],
    ),
    ROL_CAJERO: (
        "Atiende el mostrador y maneja la caja",
        ["ventas.crear", "productos.ver", "stock.ver", "clientes.ver", "clientes.gestionar", "caja.operar"],
    ),
}

rol_permisos = db.Table(
    "rol_permisos",
    db.Column("rol_id", db.Integer, db.ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
    db.Column("permiso_id", db.Integer, db.ForeignKey("permisos.id", ondelete="CASCADE"), primary_key=True),
)


class Rol(db.Model):
    __tablename__ = "roles"
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(30), nullable=False, unique=True)
    descripcion = db.Column(db.String(150))
    permisos = db.relationship("Permiso", secondary=rol_permisos, lazy="selectin")

    def __repr__(self):
        return f"<Rol {self.nombre}>"


class Permiso(db.Model):
    __tablename__ = "permisos"
    id = db.Column(db.Integer, primary_key=True)
    codigo = db.Column(db.String(50), nullable=False, unique=True)
    descripcion = db.Column(db.String(150), nullable=False)


class Usuario(UserMixin, db.Model):
    __tablename__ = "usuarios"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(40), nullable=False, unique=True)
    email = db.Column(db.String(120), nullable=False, unique=True)
    nombre = db.Column(db.String(80), nullable=False)
    apellido = db.Column(db.String(80), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    rol_id = db.Column(db.Integer, db.ForeignKey("roles.id", ondelete="RESTRICT"), nullable=False, index=True)
    empleado_id = db.Column(db.Integer, db.ForeignKey("empleados.id", ondelete="SET NULL"), unique=True)
    activo = db.Column(db.Boolean, nullable=False, default=True)
    debe_cambiar_password = db.Column(db.Boolean, nullable=False, default=False)
    # Se incrementa al cambiar la contraseña o desactivar: invalida sesiones abiertas.
    version_sesion = db.Column(db.Integer, nullable=False, default=1)
    ultimo_acceso = db.Column(db.DateTime)
    creado_en = db.Column(db.DateTime, nullable=False)

    rol = db.relationship("Rol", lazy="joined")
    empleado = db.relationship("Empleado", back_populates="usuario")

    # --- Autenticación -----------------------------------------------------
    def set_password(self, password):
        self.password_hash = generate_password_hash(password, method="scrypt")
        self.version_sesion = (self.version_sesion or 0) + 1

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def get_id(self):
        return f"{self.id}:{self.version_sesion}"

    @property
    def is_active(self):
        return bool(self.activo)

    # --- Autorización ------------------------------------------------------
    @property
    def codigos_permiso(self):
        if not hasattr(self, "_codigos_cache"):
            self._codigos_cache = {p.codigo for p in self.rol.permisos} if self.rol else set()
        return self._codigos_cache

    def tiene_permiso(self, *codigos):
        """True si el usuario tiene AL MENOS uno de los permisos indicados."""
        return any(c in self.codigos_permiso for c in codigos)

    @property
    def es_dueno(self):
        return self.rol is not None and self.rol.nombre == ROL_DUENO

    @property
    def nombre_completo(self):
        return f"{self.nombre} {self.apellido}"

    @property
    def iniciales(self):
        return (self.nombre[:1] + self.apellido[:1]).upper()


class PasswordReset(db.Model):
    __tablename__ = "password_resets"
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False, index=True)
    token_hash = db.Column(db.String(64), nullable=False, unique=True)
    expira_en = db.Column(db.DateTime, nullable=False)
    usado_en = db.Column(db.DateTime)
    creado_en = db.Column(db.DateTime, nullable=False)

    usuario = db.relationship("Usuario")
