"""Configuración de la aplicación. Todos los valores sensibles se leen desde .env."""
import os
from datetime import timedelta
from urllib.parse import quote_plus

from dotenv import load_dotenv

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
load_dotenv(os.path.join(BASE_DIR, ".env"))


def _bool(name, default=False):
    return os.getenv(name, str(default)).strip().lower() in ("1", "true", "si", "sí", "yes", "on")


def _database_uri():
    """DATABASE_URL tiene prioridad (útil para modo demo con SQLite).
    Si no está, se arma la URL de MySQL con las variables DB_*."""
    url = os.getenv("DATABASE_URL", "").strip()
    if url:
        if url.startswith("sqlite:///") and not url.startswith("sqlite:////"):
            # Ruta relativa -> relativa a la carpeta del proyecto
            rel = url.replace("sqlite:///", "", 1)
            path = os.path.join(BASE_DIR, rel)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            return "sqlite:///" + path.replace("\\", "/")
        return url
    user = quote_plus(os.getenv("DB_USER", "kiosco"))
    password = quote_plus(os.getenv("DB_PASSWORD", ""))
    host = os.getenv("DB_HOST", "127.0.0.1")
    port = os.getenv("DB_PORT", "3306")
    name = os.getenv("DB_NAME", "kiosco_db")
    return f"mysql+pymysql://{user}:{password}@{host}:{port}/{name}?charset=utf8mb4"


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "")
    SQLALCHEMY_DATABASE_URI = _database_uri()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True, "pool_recycle": 280}

    # Sesiones / cookies
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = _bool("SESSION_COOKIE_SECURE", False)  # True detrás de HTTPS
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SECURE = SESSION_COOKIE_SECURE
    REMEMBER_COOKIE_DURATION = timedelta(days=7)
    PERMANENT_SESSION_LIFETIME = timedelta(hours=int(os.getenv("SESSION_HOURS", "12")))

    # CSRF
    WTF_CSRF_TIME_LIMIT = None  # el token vive lo que dura la sesión

    # Subida de archivos
    MAX_CONTENT_LENGTH = 4 * 1024 * 1024
    UPLOAD_FOLDER = os.path.join(BASE_DIR, "app", "static", "uploads", "productos")

    # Negocio
    NEGOCIO_NOMBRE = os.getenv("NEGOCIO_NOMBRE", "Mi Kiosco")
    NEGOCIO_DIRECCION = os.getenv("NEGOCIO_DIRECCION", "")
    NEGOCIO_CUIT = os.getenv("NEGOCIO_CUIT", "")
    NEGOCIO_TELEFONO = os.getenv("NEGOCIO_TELEFONO", "")
    ZONA_HORARIA = os.getenv("ZONA_HORARIA", "America/Argentina/Buenos_Aires")
    REQUIERE_CAJA_ABIERTA = _bool("REQUIERE_CAJA_ABIERTA", True)
    POR_PAGINA = int(os.getenv("POR_PAGINA", "25"))

    # Correo (recuperación de contraseña)
    MAIL_SERVER = os.getenv("MAIL_SERVER", "")
    MAIL_PORT = int(os.getenv("MAIL_PORT", "587"))
    MAIL_USERNAME = os.getenv("MAIL_USERNAME", "")
    MAIL_PASSWORD = os.getenv("MAIL_PASSWORD", "")
    MAIL_USE_TLS = _bool("MAIL_USE_TLS", True)
    MAIL_FROM = os.getenv("MAIL_FROM", "")
    APP_URL = os.getenv("APP_URL", "").rstrip("/")

    # Seguridad de login
    LOGIN_MAX_INTENTOS = int(os.getenv("LOGIN_MAX_INTENTOS", "5"))
    LOGIN_BLOQUEO_MINUTOS = int(os.getenv("LOGIN_BLOQUEO_MINUTOS", "10"))


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False


class TestingConfig(Config):
    TESTING = True
    WTF_CSRF_ENABLED = False
    SQLALCHEMY_DATABASE_URI = "sqlite://"
    SECRET_KEY = "test"


CONFIGS = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
}
