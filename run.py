"""Punto de entrada:  python run.py

- En desarrollo y escuchando solo en 127.0.0.1 usa el servidor de Flask con recarga automática.
- Si HOST=0.0.0.0 (para usarlo desde el celular en la red local) o APP_ENV=production,
  usa Waitress, un servidor de producción, y nunca expone el depurador de Flask a la red.
- El registro del servidor se guarda en instance/servidor.log y el PID en instance/servidor.pid
  (lo usa DETENER.bat para apagar el sistema).
"""
import logging
import os
import sys
from logging.handlers import RotatingFileHandler

from app import create_app

BASE = os.path.dirname(os.path.abspath(__file__))
INSTANCE = os.path.join(BASE, "instance")
os.makedirs(INSTANCE, exist_ok=True)

app = create_app()


def _configurar_log():
    handler = RotatingFileHandler(os.path.join(INSTANCE, "servidor.log"), maxBytes=2_000_000, backupCount=3, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    raiz = logging.getLogger()
    raiz.setLevel(logging.INFO)
    # Con pythonw.exe (sin ventana) no hay consola: se quitan los handlers de consola
    if sys.stderr is None:
        for h in list(raiz.handlers):
            raiz.removeHandler(h)
    raiz.addHandler(handler)
    app.logger.addHandler(handler)


if __name__ == "__main__":
    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", "5050"))
    local = host in ("127.0.0.1", "localhost")
    if app.config.get("DEBUG") and local:
        app.run(host=host, port=port, debug=True)
    else:
        from waitress import serve

        _configurar_log()
        with open(os.path.join(INSTANCE, "servidor.pid"), "w") as f:
            f.write(str(os.getpid()))
        logging.getLogger("kioscopro").info("KioscoPro iniciado en http://%s:%s", host, port)
        if sys.stdout:
            print(f"KioscoPro sirviendo en http://{host}:{port}  (Ctrl+C para detener)")
        try:
            serve(app, host=host, port=port, threads=8)
        except Exception:
            logging.getLogger("kioscopro").exception("El servidor se detuvo por un error")
            raise
