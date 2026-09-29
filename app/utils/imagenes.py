"""Guardado seguro de imágenes de productos.

La imagen se abre con Pillow (si no es una imagen real, se rechaza), se reduce
a 800px como máximo y se vuelve a guardar como WEBP con un nombre aleatorio.
Así se descartan metadatos y cualquier contenido embebido.
"""
import os
import uuid

from flask import current_app
from PIL import Image, UnidentifiedImageError

EXTENSIONES = {"jpg", "jpeg", "png", "webp", "gif"}


class ImagenInvalida(ValueError):
    pass


def guardar_imagen(archivo):
    if not archivo or not archivo.filename:
        return None
    ext = archivo.filename.rsplit(".", 1)[-1].lower() if "." in archivo.filename else ""
    if ext not in EXTENSIONES:
        raise ImagenInvalida("Formato de imagen no permitido (usá JPG, PNG o WEBP).")
    try:
        img = Image.open(archivo.stream)
        img.verify()
        archivo.stream.seek(0)
        img = Image.open(archivo.stream)
        img = img.convert("RGBA") if img.mode in ("P", "LA", "RGBA") else img.convert("RGB")
        img.thumbnail((800, 800))
    except (UnidentifiedImageError, OSError, SyntaxError) as exc:
        raise ImagenInvalida("El archivo no es una imagen válida.") from exc
    carpeta = current_app.config["UPLOAD_FOLDER"]
    os.makedirs(carpeta, exist_ok=True)
    nombre = f"{uuid.uuid4().hex}.webp"
    img.save(os.path.join(carpeta, nombre), "WEBP", quality=82)
    return nombre


def borrar_imagen(nombre):
    if not nombre:
        return
    ruta = os.path.join(current_app.config["UPLOAD_FOLDER"], os.path.basename(nombre))
    try:
        os.remove(ruta)
    except OSError:
        pass
