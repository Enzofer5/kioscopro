"""Capa de modelos: cada clase representa una tabla de MySQL (ver database/schema.sql)."""
from .catalogo import Categoria, Marca, Producto, UnidadMedida
from .operaciones import (
    TIPOS_CAJA_ENTRADA,
    TIPOS_CAJA_SALIDA,
    TIPOS_MOV_CAJA,
    TIPOS_MOV_STOCK,
    Caja,
    CategoriaGasto,
    Compra,
    DetalleCompra,
    Gasto,
    MovimientoCaja,
    MovimientoStock,
)
from .personas import Cliente, Empleado, Proveedor
from .seguridad import (
    PERMISOS,
    ROL_ADMIN,
    ROL_CAJERO,
    ROL_DUENO,
    ROL_VENDEDOR,
    ROLES,
    PasswordReset,
    Permiso,
    Rol,
    Usuario,
    rol_permisos,
)
from .ventas import (
    ESTADO_ANULADA,
    ESTADO_COMPLETADA,
    ESTADO_DEVUELTA,
    ESTADOS_VENTA,
    AnulacionVenta,
    DetalleVenta,
    MetodoPago,
    Pago,
    Venta,
)

__all__ = [n for n in dir() if not n.startswith("_")]
