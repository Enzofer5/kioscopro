"""Funciones auxiliares: fechas, dinero, parseo seguro de datos de formularios."""
from datetime import date, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from zoneinfo import ZoneInfo

from flask import current_app

CENTAVO = Decimal("0.01")
MILESIMA = Decimal("0.001")


def ahora():
    """Fecha y hora local del negocio (naive, para guardar en DATETIME)."""
    tz = ZoneInfo(current_app.config.get("ZONA_HORARIA", "America/Argentina/Buenos_Aires"))
    return datetime.now(tz).replace(tzinfo=None, microsecond=0)


def hoy():
    return ahora().date()


def redondear(valor, q=CENTAVO):
    return Decimal(valor).quantize(q, rounding=ROUND_HALF_UP)


def parse_decimal(valor, default=None, minimo=None, maximo=None):
    """Acepta '1234.56', '1.234,56' o '1234,56'. Devuelve Decimal o default."""
    if valor is None:
        return default
    if isinstance(valor, (int, float, Decimal)):
        texto = str(valor)
    else:
        texto = str(valor).strip().replace("$", "").replace(" ", "")
        if not texto:
            return default
        if "," in texto:
            texto = texto.replace(".", "").replace(",", ".")
    try:
        numero = Decimal(texto)
    except (InvalidOperation, ValueError):
        return default
    if not numero.is_finite():
        return default
    if minimo is not None and numero < Decimal(str(minimo)):
        return default
    if maximo is not None and numero > Decimal(str(maximo)):
        return default
    return numero


def parse_int(valor, default=None):
    try:
        return int(str(valor).strip())
    except (TypeError, ValueError):
        return default


def parse_fecha(valor, default=None):
    if not valor:
        return default
    if isinstance(valor, date):
        return valor
    for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(str(valor).strip(), fmt).date()
        except ValueError:
            continue
    return default


def limpiar(valor, max_len=None):
    """Recorta espacios; devuelve None si queda vacío."""
    if valor is None:
        return None
    texto = " ".join(str(valor).split())
    if not texto:
        return None
    return texto[:max_len] if max_len else texto


def formato_moneda(valor):
    """1234.5 -> '$ 1.234,50' (formato argentino)."""
    if valor is None:
        valor = 0
    numero = redondear(valor)
    signo = "-" if numero < 0 else ""
    entero, dec = f"{abs(numero):.2f}".split(".")
    entero = f"{int(entero):,}".replace(",", ".")
    return f"{signo}$ {entero},{dec}"


def formato_cantidad(valor):
    if valor is None:
        return "0"
    numero = Decimal(valor)
    if numero == numero.to_integral():
        return f"{int(numero):,}".replace(",", ".")
    texto = f"{numero.normalize():f}"
    return texto.replace(".", ",")


def formato_fecha(valor, con_hora=True):
    if not valor:
        return ""
    if isinstance(valor, datetime):
        return valor.strftime("%d/%m/%Y %H:%M" if con_hora else "%d/%m/%Y")
    if isinstance(valor, date):
        return valor.strftime("%d/%m/%Y")
    return str(valor)


def rango_periodo(periodo, desde=None, hasta=None):
    """Devuelve (fecha_desde, fecha_hasta, etiqueta) para filtros de reportes."""
    d = hoy()
    if periodo == "ayer":
        a = d - timedelta(days=1)
        return a, a, "Ayer"
    if periodo == "7dias":
        return d - timedelta(days=6), d, "Últimos 7 días"
    if periodo == "mes":
        return d.replace(day=1), d, "Este mes"
    if periodo == "mes_anterior":
        fin = d.replace(day=1) - timedelta(days=1)
        return fin.replace(day=1), fin, "Mes anterior"
    if periodo == "rango":
        f1 = parse_fecha(desde, d)
        f2 = parse_fecha(hasta, d)
        if f1 > f2:
            f1, f2 = f2, f1
        return f1, f2, f"{formato_fecha(f1)} al {formato_fecha(f2)}"
    return d, d, "Hoy"


def inicio_dia(f):
    return datetime.combine(f, datetime.min.time())


def fin_dia(f):
    return datetime.combine(f + timedelta(days=1), datetime.min.time())


def a_fecha(valor):
    """Normaliza el resultado de func.date() (str en SQLite, date en MySQL)."""
    if isinstance(valor, datetime):
        return valor.date()
    if isinstance(valor, date):
        return valor
    return datetime.strptime(str(valor)[:10], "%Y-%m-%d").date()
