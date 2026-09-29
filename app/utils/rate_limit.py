"""Limitador simple de intentos de login en memoria.

Suficiente para una instalación de un solo proceso (el caso típico de un kiosco).
Si se despliega con varios workers, cada proceso lleva su propio conteo; para
entornos grandes conviene reemplazarlo por Redis.
"""
import threading
import time

_lock = threading.Lock()
_fallos = {}


def _clave(ip, usuario):
    return f"{ip}|{(usuario or '').lower()}"


def bloqueado(ip, usuario, max_intentos, minutos):
    """Devuelve los segundos restantes de bloqueo (0 si no está bloqueado)."""
    ventana = minutos * 60
    ahora = time.time()
    with _lock:
        intentos = [t for t in _fallos.get(_clave(ip, usuario), []) if ahora - t < ventana]
        _fallos[_clave(ip, usuario)] = intentos
        if len(intentos) >= max_intentos:
            return int(ventana - (ahora - intentos[0])) + 1
    return 0


def registrar_fallo(ip, usuario):
    with _lock:
        _fallos.setdefault(_clave(ip, usuario), []).append(time.time())


def limpiar(ip, usuario):
    with _lock:
        _fallos.pop(_clave(ip, usuario), None)
