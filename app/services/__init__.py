"""Capa de servicios: reglas de negocio y transacciones.

Las rutas nunca modifican varias tablas por su cuenta: llaman a un servicio,
que valida, ejecuta todo en una transacción y lanza ErrorNegocio con un
mensaje apto para mostrar al usuario si algo no se cumple.
"""


class ErrorNegocio(Exception):
    """Error de validación o regla de negocio (mensaje apto para el usuario)."""
