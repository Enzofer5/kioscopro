"""Ventas, detalle, pagos, métodos de pago y anulaciones."""
from ..extensions import db

ESTADO_COMPLETADA = "completada"
ESTADO_ANULADA = "anulada"
ESTADO_DEVUELTA = "devuelta"
ESTADOS_VENTA = (ESTADO_COMPLETADA, ESTADO_ANULADA, ESTADO_DEVUELTA)


class MetodoPago(db.Model):
    __tablename__ = "metodos_pago"
    id = db.Column(db.Integer, primary_key=True)
    codigo = db.Column(db.String(20), nullable=False, unique=True)
    nombre = db.Column(db.String(40), nullable=False, unique=True)
    es_efectivo = db.Column(db.Boolean, nullable=False, default=False)
    orden = db.Column(db.SmallInteger, nullable=False, default=0)
    activo = db.Column(db.Boolean, nullable=False, default=True)


class Venta(db.Model):
    __tablename__ = "ventas"
    id = db.Column(db.Integer, primary_key=True)
    fecha = db.Column(db.DateTime, nullable=False, index=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id", ondelete="RESTRICT"), nullable=False, index=True)
    cliente_id = db.Column(db.Integer, db.ForeignKey("clientes.id", ondelete="RESTRICT"), index=True)
    caja_id = db.Column(db.Integer, db.ForeignKey("cajas.id", ondelete="RESTRICT"), index=True)
    subtotal = db.Column(db.Numeric(12, 2), nullable=False)
    descuento = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    total = db.Column(db.Numeric(12, 2), nullable=False)
    estado = db.Column(db.String(15), nullable=False, default=ESTADO_COMPLETADA)
    observaciones = db.Column(db.String(255))

    usuario = db.relationship("Usuario", lazy="joined")
    cliente = db.relationship("Cliente", lazy="joined")
    caja = db.relationship("Caja", back_populates="ventas")
    detalles = db.relationship("DetalleVenta", back_populates="venta", cascade="all, delete-orphan", lazy="selectin")
    pagos = db.relationship("Pago", back_populates="venta", cascade="all, delete-orphan", lazy="selectin")
    anulacion = db.relationship("AnulacionVenta", back_populates="venta", uselist=False, lazy="joined")

    __table_args__ = (
        db.CheckConstraint("subtotal >= 0", name="subtotal_pos"),
        db.CheckConstraint("descuento >= 0", name="descuento_pos"),
        db.CheckConstraint("total >= 0", name="total_pos"),
        db.CheckConstraint("estado IN ('completada','anulada','devuelta')", name="estado_valido"),
        db.Index("ix_ventas_estado_fecha", "estado", "fecha"),
    )

    @property
    def metodo_principal(self):
        return self.pagos[0].metodo if self.pagos else None

    @property
    def costo_total(self):
        return sum((d.cantidad * d.costo_unitario for d in self.detalles), 0)


class DetalleVenta(db.Model):
    __tablename__ = "detalle_ventas"
    id = db.Column(db.Integer, primary_key=True)
    venta_id = db.Column(db.Integer, db.ForeignKey("ventas.id", ondelete="CASCADE"), nullable=False, index=True)
    producto_id = db.Column(db.Integer, db.ForeignKey("productos.id", ondelete="RESTRICT"), nullable=False, index=True)
    cantidad = db.Column(db.Numeric(12, 3), nullable=False)
    precio_unitario = db.Column(db.Numeric(12, 2), nullable=False)  # precio de venta congelado
    costo_unitario = db.Column(db.Numeric(12, 2), nullable=False)   # precio de compra congelado
    descuento = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    subtotal = db.Column(db.Numeric(12, 2), nullable=False)          # cantidad*precio - descuento

    venta = db.relationship("Venta", back_populates="detalles")
    producto = db.relationship("Producto", lazy="joined")

    __table_args__ = (
        db.CheckConstraint("cantidad > 0", name="cantidad_pos"),
        db.CheckConstraint("precio_unitario >= 0", name="precio_pos"),
        db.CheckConstraint("costo_unitario >= 0", name="costo_pos"),
        db.CheckConstraint("descuento >= 0", name="descuento_pos"),
        db.CheckConstraint("subtotal >= 0", name="subtotal_pos"),
    )


class Pago(db.Model):
    __tablename__ = "pagos"
    id = db.Column(db.Integer, primary_key=True)
    venta_id = db.Column(db.Integer, db.ForeignKey("ventas.id", ondelete="CASCADE"), nullable=False, index=True)
    metodo_pago_id = db.Column(db.Integer, db.ForeignKey("metodos_pago.id", ondelete="RESTRICT"), nullable=False, index=True)
    monto = db.Column(db.Numeric(12, 2), nullable=False)
    monto_recibido = db.Column(db.Numeric(12, 2))  # solo efectivo, para calcular vuelto

    venta = db.relationship("Venta", back_populates="pagos")
    metodo = db.relationship("MetodoPago", lazy="joined")

    __table_args__ = (
        db.CheckConstraint("monto > 0", name="monto_pos"),
        db.CheckConstraint("monto_recibido IS NULL OR monto_recibido >= monto", name="recibido_valido"),
    )

    @property
    def vuelto(self):
        if self.monto_recibido is None:
            return None
        return self.monto_recibido - self.monto


class AnulacionVenta(db.Model):
    __tablename__ = "anulaciones_venta"
    id = db.Column(db.Integer, primary_key=True)
    venta_id = db.Column(db.Integer, db.ForeignKey("ventas.id", ondelete="RESTRICT"), nullable=False, unique=True)
    tipo = db.Column(db.String(12), nullable=False)
    motivo = db.Column(db.String(255), nullable=False)
    reintegra_stock = db.Column(db.Boolean, nullable=False, default=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id", ondelete="RESTRICT"), nullable=False, index=True)
    caja_id = db.Column(db.Integer, db.ForeignKey("cajas.id", ondelete="RESTRICT"), index=True)
    fecha = db.Column(db.DateTime, nullable=False)

    venta = db.relationship("Venta", back_populates="anulacion")
    usuario = db.relationship("Usuario", lazy="joined")

    __table_args__ = (db.CheckConstraint("tipo IN ('anulacion','devolucion')", name="tipo_valido"),)
