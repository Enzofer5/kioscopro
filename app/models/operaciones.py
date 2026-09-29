"""Compras, movimientos de stock, caja y gastos."""
from ..extensions import db

# --------------------------------------------------------------------------- Compras


class Compra(db.Model):
    __tablename__ = "compras"
    id = db.Column(db.Integer, primary_key=True)
    proveedor_id = db.Column(db.Integer, db.ForeignKey("proveedores.id", ondelete="RESTRICT"), nullable=False, index=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id", ondelete="RESTRICT"), nullable=False)
    fecha = db.Column(db.Date, nullable=False, index=True)
    numero_comprobante = db.Column(db.String(40))
    total = db.Column(db.Numeric(12, 2), nullable=False)
    observaciones = db.Column(db.String(255))
    creado_en = db.Column(db.DateTime, nullable=False)

    proveedor = db.relationship("Proveedor", lazy="joined")
    usuario = db.relationship("Usuario", lazy="joined")
    detalles = db.relationship("DetalleCompra", back_populates="compra", cascade="all, delete-orphan", lazy="selectin")

    __table_args__ = (
        db.UniqueConstraint("proveedor_id", "numero_comprobante", name="uq_compras_proveedor_comprobante"),
        db.CheckConstraint("total >= 0", name="total_pos"),
    )


class DetalleCompra(db.Model):
    __tablename__ = "detalle_compras"
    id = db.Column(db.Integer, primary_key=True)
    compra_id = db.Column(db.Integer, db.ForeignKey("compras.id", ondelete="CASCADE"), nullable=False, index=True)
    producto_id = db.Column(db.Integer, db.ForeignKey("productos.id", ondelete="RESTRICT"), nullable=False, index=True)
    cantidad = db.Column(db.Numeric(12, 3), nullable=False)
    precio_unitario = db.Column(db.Numeric(12, 2), nullable=False)
    subtotal = db.Column(db.Numeric(12, 2), nullable=False)

    compra = db.relationship("Compra", back_populates="detalles")
    producto = db.relationship("Producto", lazy="joined")

    __table_args__ = (
        db.CheckConstraint("cantidad > 0", name="cantidad_pos"),
        db.CheckConstraint("precio_unitario >= 0", name="precio_pos"),
        db.CheckConstraint("subtotal >= 0", name="subtotal_pos"),
    )


# --------------------------------------------------------------------------- Stock

TIPOS_MOV_STOCK = ("entrada", "salida", "ajuste", "venta", "compra", "anulacion")


class MovimientoStock(db.Model):
    __tablename__ = "movimientos_stock"
    id = db.Column(db.Integer, primary_key=True)
    producto_id = db.Column(db.Integer, db.ForeignKey("productos.id", ondelete="RESTRICT"), nullable=False)
    tipo = db.Column(db.String(12), nullable=False)
    cantidad = db.Column(db.Numeric(12, 3), nullable=False)  # con signo: + entra / - sale
    stock_anterior = db.Column(db.Numeric(12, 3), nullable=False)
    stock_nuevo = db.Column(db.Numeric(12, 3), nullable=False)
    motivo = db.Column(db.String(255), nullable=False)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id", ondelete="RESTRICT"), nullable=False, index=True)
    venta_id = db.Column(db.Integer, db.ForeignKey("ventas.id", ondelete="RESTRICT"), index=True)
    compra_id = db.Column(db.Integer, db.ForeignKey("compras.id", ondelete="RESTRICT"), index=True)
    fecha = db.Column(db.DateTime, nullable=False, index=True)

    producto = db.relationship("Producto", lazy="joined")
    usuario = db.relationship("Usuario", lazy="joined")

    __table_args__ = (
        db.CheckConstraint("tipo IN ('entrada','salida','ajuste','venta','compra','anulacion')", name="tipo_valido"),
        db.CheckConstraint("cantidad <> 0", name="cantidad_no_cero"),
        db.CheckConstraint("stock_nuevo >= 0", name="stock_nuevo_pos"),
        db.Index("ix_movimientos_stock_producto_fecha", "producto_id", "fecha"),
    )


# --------------------------------------------------------------------------- Caja

TIPOS_MOV_CAJA = ("venta", "ingreso", "egreso", "retiro", "gasto", "anulacion")
TIPOS_CAJA_ENTRADA = ("venta", "ingreso")
TIPOS_CAJA_SALIDA = ("egreso", "retiro", "gasto", "anulacion")


class Caja(db.Model):
    __tablename__ = "cajas"
    id = db.Column(db.Integer, primary_key=True)
    usuario_apertura_id = db.Column(db.Integer, db.ForeignKey("usuarios.id", ondelete="RESTRICT"), nullable=False)
    fecha_apertura = db.Column(db.DateTime, nullable=False, index=True)
    monto_inicial = db.Column(db.Numeric(12, 2), nullable=False)
    usuario_cierre_id = db.Column(db.Integer, db.ForeignKey("usuarios.id", ondelete="RESTRICT"))
    fecha_cierre = db.Column(db.DateTime)
    monto_esperado = db.Column(db.Numeric(12, 2))
    monto_declarado = db.Column(db.Numeric(12, 2))
    diferencia = db.Column(db.Numeric(12, 2))
    observaciones = db.Column(db.String(255))
    # 1 mientras está abierta, NULL al cerrarse. Con UNIQUE garantiza a nivel
    # base de datos que nunca haya dos cajas abiertas al mismo tiempo.
    abierta = db.Column(db.Boolean, unique=True, default=True)

    usuario_apertura = db.relationship("Usuario", foreign_keys=[usuario_apertura_id], lazy="joined")
    usuario_cierre = db.relationship("Usuario", foreign_keys=[usuario_cierre_id], lazy="joined")
    movimientos = db.relationship("MovimientoCaja", back_populates="caja", lazy="dynamic")
    ventas = db.relationship("Venta", back_populates="caja", lazy="dynamic")

    __table_args__ = (
        db.CheckConstraint("monto_inicial >= 0", name="monto_inicial_pos"),
        db.CheckConstraint("abierta IS NULL OR abierta = 1", name="abierta_valida"),
        db.CheckConstraint(
            "(abierta = 1 AND fecha_cierre IS NULL) OR (abierta IS NULL AND fecha_cierre IS NOT NULL)",
            name="estado_coherente",
        ),
    )

    @property
    def estado(self):
        return "abierta" if self.abierta else "cerrada"


class MovimientoCaja(db.Model):
    __tablename__ = "movimientos_caja"
    id = db.Column(db.Integer, primary_key=True)
    caja_id = db.Column(db.Integer, db.ForeignKey("cajas.id", ondelete="RESTRICT"), nullable=False, index=True)
    tipo = db.Column(db.String(12), nullable=False)
    concepto = db.Column(db.String(150), nullable=False)
    monto = db.Column(db.Numeric(12, 2), nullable=False)
    metodo_pago_id = db.Column(db.Integer, db.ForeignKey("metodos_pago.id", ondelete="RESTRICT"), nullable=False)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id", ondelete="RESTRICT"), nullable=False)
    venta_id = db.Column(db.Integer, db.ForeignKey("ventas.id", ondelete="RESTRICT"), index=True)
    gasto_id = db.Column(db.Integer, db.ForeignKey("gastos.id", ondelete="RESTRICT"), unique=True)
    fecha = db.Column(db.DateTime, nullable=False)

    caja = db.relationship("Caja", back_populates="movimientos")
    metodo = db.relationship("MetodoPago", lazy="joined")
    usuario = db.relationship("Usuario", lazy="joined")

    __table_args__ = (
        db.CheckConstraint("tipo IN ('venta','ingreso','egreso','retiro','gasto','anulacion')", name="tipo_valido"),
        db.CheckConstraint("monto > 0", name="monto_pos"),
    )

    @property
    def es_entrada(self):
        return self.tipo in TIPOS_CAJA_ENTRADA


# --------------------------------------------------------------------------- Gastos


class CategoriaGasto(db.Model):
    __tablename__ = "categorias_gasto"
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(60), nullable=False, unique=True)
    activo = db.Column(db.Boolean, nullable=False, default=True)


class Gasto(db.Model):
    __tablename__ = "gastos"
    id = db.Column(db.Integer, primary_key=True)
    categoria_id = db.Column(db.Integer, db.ForeignKey("categorias_gasto.id", ondelete="RESTRICT"), nullable=False, index=True)
    descripcion = db.Column(db.String(200), nullable=False)
    monto = db.Column(db.Numeric(12, 2), nullable=False)
    metodo_pago_id = db.Column(db.Integer, db.ForeignKey("metodos_pago.id", ondelete="RESTRICT"), nullable=False)
    fecha = db.Column(db.Date, nullable=False, index=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id", ondelete="RESTRICT"), nullable=False)
    creado_en = db.Column(db.DateTime, nullable=False)

    categoria = db.relationship("CategoriaGasto", lazy="joined")
    metodo = db.relationship("MetodoPago", lazy="joined")
    usuario = db.relationship("Usuario", lazy="joined")
    movimiento_caja = db.relationship("MovimientoCaja", uselist=False, primaryjoin="Gasto.id == MovimientoCaja.gasto_id", viewonly=True)

    __table_args__ = (db.CheckConstraint("monto > 0", name="monto_pos"),)
