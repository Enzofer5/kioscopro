import pytest
from flask import g

from app import create_app
from app.cli import _cargar_demo, cargar_datos_base
from app.extensions import db
from app.utils import rate_limit


@pytest.fixture()
def app():
    rate_limit._fallos.clear()
    app = create_app("testing")
    # Las pruebas mantienen un app context abierto para consultar la base; en producción
    # cada request tiene su propio "g". Se limpia el usuario cacheado para simularlo.
    @app.before_request
    def _limpiar_g():
        g.pop("_login_user", None)

    with app.app_context():
        db.create_all()
        cargar_datos_base()
        _cargar_demo(dias=10)
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


def login(client, usuario, clave):
    return client.post("/auth/login", data={"usuario": usuario, "password": clave}, follow_redirects=False)


CLAVES = {"dueno": "Dueno1234", "admin": "Admin1234", "vendedor": "Vende1234", "cajero": "Caja1234"}


@pytest.fixture()
def como(client):
    def _como(usuario):
        client.get("/")  # asegura cookie
        client.post("/auth/logout")
        r = login(client, usuario, CLAVES[usuario])
        assert r.status_code == 302, r.data[:500]
        return client
    return _como
