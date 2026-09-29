"""Empleados, clientes y proveedores."""
from ..extensions import db


class Empleado(db.Model):
    __tablename__ = "empleados"
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(80), nullable=False)
    apellido = db.Column(db.String(80), nullable=False)
    dni = db.Column(db.String(15), nullable=False, unique=True)
    telefono = db.Column(db.String(30))
    email = db.Column(db.String(120))
    puesto = db.Column(db.String(60), nullable=False)
    fecha_ingreso = db.Column(db.Date, nullable=False)
    activo = db.Column(db.Boolean, nullable=False, default=True)
    creado_en = db.Column(db.DateTime, nullable=False)

    usuario = db.relationship("Usuario", back_populates="empleado", uselist=False)

    __table_args__ = (db.Index("ix_empleados_apellido_nombre", "apellido", "nombre"),)

    @property
    def nombre_completo(self):
        return f"{self.apellido}, {self.nombre}"


class Cliente(db.Model):
    __tablename__ = "clientes"
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(80), nullable=False)
    apellido = db.Column(db.String(80), nullable=False)
    dni = db.Column(db.String(15), unique=True)
    telefono = db.Column(db.String(30))
    email = db.Column(db.String(120))
    direccion = db.Column(db.String(200))
    fecha_registro = db.Column(db.DateTime, nullable=False)
    activo = db.Column(db.Boolean, nullable=False, default=True)

    __table_args__ = (db.Index("ix_clientes_apellido_nombre", "apellido", "nombre"),)

    @property
    def nombre_completo(self):
        return f"{self.apellido}, {self.nombre}"


class Proveedor(db.Model):
    __tablename__ = "proveedores"
    id = db.Column(db.Integer, primary_key=True)
    razon_social = db.Column(db.String(150), nullable=False, index=True)
    cuit = db.Column(db.String(13), unique=True)
    telefono = db.Column(db.String(30))
    email = db.Column(db.String(120))
    direccion = db.Column(db.String(200))
    contacto = db.Column(db.String(100))
    activo = db.Column(db.Boolean, nullable=False, default=True)
    observaciones = db.Column(db.Text)
    creado_en = db.Column(db.DateTime, nullable=False)
