"""Envío de correos por SMTP (configurado en .env)."""
import smtplib
from email.message import EmailMessage

from flask import current_app


def mail_configurado():
    return bool(current_app.config.get("MAIL_SERVER"))


def enviar_mail(destinatario, asunto, texto):
    """Envía un correo de texto plano. Devuelve True si se envió.
    Si no hay SMTP configurado, registra el contenido en el log del servidor
    (solo visible para quien administra el servidor)."""
    cfg = current_app.config
    if not mail_configurado():
        current_app.logger.warning("SMTP no configurado. Correo para %s | %s\n%s", destinatario, asunto, texto)
        return False
    msg = EmailMessage()
    msg["Subject"] = asunto
    msg["From"] = cfg.get("MAIL_FROM") or cfg.get("MAIL_USERNAME")
    msg["To"] = destinatario
    msg.set_content(texto)
    try:
        with smtplib.SMTP(cfg["MAIL_SERVER"], cfg["MAIL_PORT"], timeout=15) as smtp:
            if cfg.get("MAIL_USE_TLS"):
                smtp.starttls()
            if cfg.get("MAIL_USERNAME"):
                smtp.login(cfg["MAIL_USERNAME"], cfg["MAIL_PASSWORD"])
            smtp.send_message(msg)
        return True
    except (smtplib.SMTPException, OSError) as exc:
        current_app.logger.error("No se pudo enviar el correo a %s: %s", destinatario, exc)
        return False
