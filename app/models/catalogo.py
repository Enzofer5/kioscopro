"""Productos y sus tablas de referencia (categorías, marcas, unidades)."""
from decimal import Decimal

from ..extensions import db


class Categoria(db.Model):
    __tablename__ = "categorias"
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(60), nullable=False, unique=True)
    activo = db.Column(db.Boolean, nullable=False, default=True)


class Marca(db.Model):
    __tablename__ = "marcas"
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(60), nullable=False, unique=True)
    activo = db.Column(db.Boolean, nullable=False, default=True)


class UnidadMedida(db.Model):
    __tablename__ = "unidades_medida"
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(30), nullable=False, unique=True)
    abreviatura = db.Column(db.String(10), nullable=False, unique=True)
    permite_decimales = db.Column(db.Boolean, nullable=False, default=False)


class Producto(db.Model):
    __tablename__ = "productos"
    id = db.Column(db.Integer, primary_key=True)
    codigo_barras = db.Column(db.String(32), unique=True)
    nombre = db.Column(db.String(120), nullable=False, index=True)
    descripcion = db.Column(db.Text)
    categoria_id = db.Column(db.Integer, db.ForeignKey("categorias.id", ondelete="RESTRICT"), nullable=False, index=True)
    marca_id = db.Column(db.Integer, db.ForeignKey("marcas.id", ondelete="RESTRICT"), index=True)
    unidad_id = db.Column(db.Integer, db.ForeignKey("unidades_medida.id", ondelete="RESTRICT"), nullable=False)
    precio_compra = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    precio_venta = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    stock_actual = db.Column(db.Numeric(12, 3), nullable=False, default=0)
    stock_minimo = db.Column(db.Numeric(12, 3), nullable=False, default=0)
    imagen = db.Column(db.String(255))
    activo = db.Column(db.Boolean, nullable=False, default=True, index=True)
    creado_en = db.Column(db.DateTime, nullable=False)
    actualizado_en = db.Column(db.DateTime, nullable=False)

    categoria = db.relationship("Categoria", lazy="joined")
    marca = db.relationship("Marca", lazy="joined")
    unidad = db.relationship("UnidadMedida", lazy="joined")

    __table_args__ = (
        db.CheckConstraint("precio_compra >= 0", name="precio_compra_pos"),
        db.CheckConstraint("precio_venta >= 0", name="precio_venta_pos"),
        db.CheckConstraint("stock_actual >= 0", name="stock_actual_pos"),
        db.CheckConstraint("stock_minimo >= 0", name="stock_minimo_pos"),
        db.Index("ix_productos_stock", "stock_actual", "stock_minimo"),
    )

    @property
    def agotado(self):
        return Decimal(self.stock_actual or 0) <= 0

    @property
    def bajo_stock(self):
        return not self.agotado and Decimal(self.stock_actual or 0) <= Decimal(self.stock_minimo or 0)

    @property
    def margen_pct(self):
        compra = Decimal(self.precio_compra or 0)
        if compra <= 0:
            return None
        return (Decimal(self.precio_venta or 0) - compra) / compra * 100

    def to_pos(self):
        """Representación mínima para el POS (JSON)."""
        return {
            "id": self.id,
            "codigo": self.codigo_barras or "",
            "nombre": self.nombre,
            "marca": self.marca.nombre if self.marca else "",
            "precio": float(self.precio_venta),
            "stock": float(self.stock_actual),
            "unidad": self.unidad.abreviatura if self.unidad else "u",
            "decimales": bool(self.unidad and self.unidad.permite_decimales),
            "imagen": self.imagen or "",
        }
