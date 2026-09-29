"""Pruebas de los flujos principales: permisos, POS, stock, caja, compras y anulaciones."""
from decimal import Decimal

from sqlalchemy import func, select

from app.extensions import db
from app.models import Caja, MovimientoCaja, MovimientoStock, Producto, Usuario, Venta

PAGINAS = [
    "/", "/ventas/pos", "/ventas/historial", "/ventas/historial?fecha=2020-01-01", "/productos/", "/productos/?estado=activos",
    "/productos/nuevo", "/productos/catalogo/categorias", "/productos/catalogo/marcas", "/productos/1", "/productos/1/editar",
    "/stock/", "/stock/?tipo=venta", "/stock/movimiento", "/stock/alertas/bajo", "/stock/alertas/agotados",
    "/compras/", "/compras/?desde=2020-01-01", "/compras/nueva", "/compras/1", "/proveedores/", "/proveedores/?estado=activos",
    "/proveedores/nuevo", "/proveedores/1", "/proveedores/1/editar", "/clientes/", "/clientes/?q=a", "/clientes/nuevo",
    "/clientes/1", "/clientes/1/editar", "/caja/", "/caja/historial", "/caja/1", "/gastos/", "/gastos/categorias",
    "/empleados/", "/empleados/nuevo", "/empleados/1/editar", "/usuarios/", "/usuarios/nuevo", "/usuarios/2/editar",
    "/reportes/ventas", "/reportes/ventas?periodo=7dias", "/reportes/productos", "/reportes/ganancias?agrupacion=semana",
    "/reportes/ganancias?periodo=rango&desde=2020-01-01&hasta=2030-01-01&agrupacion=mes", "/reportes/pagos?periodo=mes_anterior",
    "/auth/perfil", "/auth/cambiar-password", "/ventas/1", "/ventas/1/comprobante",
]

ADMINISTRATIVAS = ["/ventas/historial", "/productos/nuevo", "/compras/", "/proveedores/", "/caja/historial", "/gastos/",
                   "/empleados/", "/usuarios/", "/reportes/ventas", "/stock/movimiento", "/ventas/1"]


def test_dueno_ve_todo(como):
    c = como("dueno")
    for url in PAGINAS:
        r = c.get(url)
        assert r.status_code == 200, (url, r.status_code, r.data[:300])


def test_vendedor_no_accede_a_informacion_sensible(como):
    c = como("vendedor")
    for url in ADMINISTRATIVAS + ["/caja/"]:
        assert c.get(url).status_code == 403, url
    for url in ["/", "/ventas/pos", "/productos/?estado=activos", "/productos/1", "/clientes/?q=a", "/stock/alertas/bajo"]:
        assert c.get(url).status_code == 200, url
    html = c.get("/").get_data(as_text=True)
    assert "Ventas del mes" not in html and "Ganancia" not in html
    # El costo no viaja al vendedor
    r = c.get("/ventas/api/productos?q=coca").get_json()
    assert r["productos"] and "costo" not in r["productos"][0]
    assert "Costo" not in c.get("/productos/?estado=activos").get_data(as_text=True)


def test_cajero_opera_caja_pero_no_reportes(como):
    c = como("cajero")
    assert c.get("/caja/").status_code == 200
    assert c.get("/reportes/ventas").status_code == 403
    assert c.get("/usuarios/").status_code == 403


def test_rutas_protegidas_sin_sesion(client):
    r = client.get("/productos/")
    assert r.status_code == 302 and "/auth/login" in r.headers["Location"]


def test_login_incorrecto_y_bloqueo(client):
    for _ in range(5):
        r = client.post("/auth/login", data={"usuario": "admin", "password": "mal"})
        assert r.status_code == 200
    r = client.post("/auth/login", data={"usuario": "admin", "password": "Admin1234"})
    assert r.status_code == 429


def _abrir_caja(c, monto="10000"):
    r = c.post("/caja/abrir", data={"monto_inicial": monto}, follow_redirects=True)
    assert r.status_code == 200


def test_flujo_venta_completo(app, como):
    c = como("cajero")
    prod = db.session.scalar(select(Producto).where(Producto.codigo_barras == "7790895000997"))
    stock_ini = Decimal(prod.stock_actual)

    # Sin caja abierta no se puede vender
    r = c.post("/ventas/api/confirmar", json={"items": [{"producto_id": prod.id, "cantidad": 1}], "metodo_pago": "efectivo"})
    assert r.status_code == 400 and "caja" in r.get_json()["error"].lower()

    _abrir_caja(c)
    datos = {
        "items": [{"producto_id": prod.id, "cantidad": 3, "descuento_pct": 10}],
        "metodo_pago": "efectivo", "descuento_tipo": "monto", "descuento_valor": 70, "monto_recibido": 5000,
        "cliente_id": 1,
    }
    r = c.post("/ventas/api/confirmar", json=datos)
    body = r.get_json()
    assert r.status_code == 200, body
    venta = db.session.get(Venta, body["venta_id"])
    # 3 x 1100 = 3300; -10% = 330 -> 2970; -70 = 2900
    assert venta.subtotal == Decimal("3300.00")
    assert venta.descuento == Decimal("400.00")
    assert venta.total == Decimal("2900.00")
    assert venta.pagos[0].vuelto == Decimal("2100.00")
    assert venta.usuario.username == "cajero" and venta.cliente_id == 1
    db.session.refresh(prod)
    assert Decimal(prod.stock_actual) == stock_ini - 3
    mov = db.session.scalar(select(MovimientoStock).where(MovimientoStock.venta_id == venta.id))
    assert mov.tipo == "venta" and mov.cantidad == Decimal("-3")
    assert db.session.scalar(select(MovimientoCaja).where(MovimientoCaja.venta_id == venta.id)).monto == Decimal("2900.00")
    assert c.get(f"/ventas/{venta.id}/comprobante").status_code == 200

    # No se puede vender más que el stock
    r = c.post("/ventas/api/confirmar", json={"items": [{"producto_id": prod.id, "cantidad": 99999}], "metodo_pago": "debito"})
    assert r.status_code == 400 and "Stock insuficiente" in r.get_json()["error"]
    # El precio no se puede manipular desde el cliente: se ignora cualquier "precio" enviado
    r = c.post("/ventas/api/confirmar", json={"items": [{"producto_id": prod.id, "cantidad": 1, "precio": 1}], "metodo_pago": "debito"})
    assert db.session.get(Venta, r.get_json()["venta_id"]).total == Decimal("1100.00")

    # Anulación (admin): stock vuelve y se registra egreso en caja
    c = como("admin")
    stock_antes = Decimal(db.session.get(Producto, prod.id).stock_actual)
    r = c.post(f"/ventas/{venta.id}/anular", data={"tipo": "anulacion", "motivo": "Error de carga"}, follow_redirects=True)
    assert r.status_code == 200
    db.session.expire_all()
    venta = db.session.get(Venta, venta.id)
    assert venta.estado == "anulada" and venta.anulacion.usuario.username == "admin"
    assert Decimal(db.session.get(Producto, prod.id).stock_actual) == stock_antes + 3
    assert db.session.scalar(select(func.count(MovimientoCaja.id)).where(MovimientoCaja.venta_id == venta.id, MovimientoCaja.tipo == "anulacion")) == 1
    # No se puede anular dos veces
    c.post(f"/ventas/{venta.id}/anular", data={"tipo": "anulacion", "motivo": "Otra vez"})
    assert db.session.scalar(select(func.count()).select_from(Venta).where(Venta.id == venta.id)) == 1


def test_caja_arqueo_y_cierre(como):
    c = como("cajero")
    _abrir_caja(c, "5000")
    assert c.post("/caja/abrir", data={"monto_inicial": "1"}, follow_redirects=True).status_code == 200  # rechaza segunda
    assert db.session.scalar(select(func.count(Caja.id)).where(Caja.abierta.is_(True))) == 1
    c.post("/ventas/api/confirmar", json={"items": [{"producto_id": 1, "cantidad": 2}], "metodo_pago": "efectivo"})
    c.post("/ventas/api/confirmar", json={"items": [{"producto_id": 1, "cantidad": 1}], "metodo_pago": "mercadopago"})
    c.post("/caja/movimiento", data={"tipo": "ingreso", "concepto": "Cambio", "monto": "1000"})
    c.post("/caja/movimiento", data={"tipo": "retiro", "concepto": "Retiro dueño", "monto": "3000"})
    r = c.post("/caja/cerrar", data={"monto_declarado": "5150"}, follow_redirects=True)
    assert r.status_code == 200
    caja = db.session.scalar(select(Caja).order_by(Caja.id.desc()))
    # 5000 + 2200 (efectivo) + 1000 - 3000 = 5200
    assert caja.monto_esperado == Decimal("5200.00")
    assert caja.diferencia == Decimal("-50.00")
    assert caja.abierta is None and caja.fecha_cierre is not None


def test_compra_suma_stock_y_actualiza_costo(como):
    c = como("admin")
    p = db.session.get(Producto, 2)
    antes = Decimal(p.stock_actual)
    r = c.post("/compras/api/confirmar", json={
        "proveedor_id": 1, "fecha": "2026-01-10", "numero_comprobante": "A-0001-999",
        "actualizar_costos": True, "items": [{"producto_id": 2, "cantidad": 12, "precio": "1400,50"}],
    })
    assert r.status_code == 200, r.get_json()
    db.session.expire_all()
    p = db.session.get(Producto, 2)
    assert Decimal(p.stock_actual) == antes + 12 and p.precio_compra == Decimal("1400.50")
    # Comprobante duplicado
    r = c.post("/compras/api/confirmar", json={"proveedor_id": 1, "fecha": "2026-01-10", "numero_comprobante": "A-0001-999",
                                               "items": [{"producto_id": 2, "cantidad": 1, "precio": 1}]})
    assert r.status_code == 400


def test_ajuste_stock_y_producto(como):
    c = como("admin")
    r = c.post("/stock/movimiento", data={"producto_id": 3, "tipo": "ajuste", "cantidad": "7", "motivo": "Recuento"}, follow_redirects=True)
    assert r.status_code == 200
    assert db.session.get(Producto, 3).stock_actual == Decimal("7")
    r = c.post("/productos/nuevo", data={"nombre": "Producto test", "categoria_id": 1, "unidad_id": 1, "precio_compra": "100",
                                          "precio_venta": "150", "stock_minimo": "2", "stock_inicial": "10", "codigo_barras": "123456"})
    assert r.status_code == 302
    p = db.session.scalar(select(Producto).where(Producto.codigo_barras == "123456"))
    assert p.stock_actual == Decimal("10")
    # Código duplicado
    r = c.post("/productos/nuevo", data={"nombre": "Otro", "categoria_id": 1, "unidad_id": 1, "precio_compra": "1",
                                          "precio_venta": "2", "codigo_barras": "123456"})
    assert "Ya existe otro producto" in r.get_data(as_text=True)


def test_gasto_afecta_ganancia(como, app):
    c = como("dueno")
    antes = c.get("/reportes/ganancias?periodo=hoy").get_data(as_text=True)
    r = c.post("/gastos/", data={"categoria_id": 1, "descripcion": "Prueba", "monto": "12345", "metodo_pago_id": 2, "fecha": ""}, follow_redirects=True)
    assert r.status_code == 200
    despues = c.get("/reportes/ganancias?periodo=hoy").get_data(as_text=True)
    assert "12.345,00" in despues and antes != despues


def test_usuarios_reglas(como):
    c = como("admin")
    dueno = db.session.scalar(select(Usuario).where(Usuario.username == "dueno"))
    assert c.get(f"/usuarios/{dueno.id}/editar").status_code == 403
    r = c.post("/usuarios/nuevo", data={"nombre": "N", "apellido": "U", "username": "nuevo", "email": "n@x.com",
                                         "rol_id": dueno.rol_id, "password": "Clave1234", "password2": "Clave1234"}, follow_redirects=True)
    assert "Seleccioná un rol válido" in r.get_data(as_text=True)
    admin = db.session.scalar(select(Usuario).where(Usuario.username == "admin"))
    r = c.post(f"/usuarios/{admin.id}/estado", follow_redirects=True)
    assert "No podés desactivar tu propio usuario" in r.get_data(as_text=True)


def test_cambio_password_invalida_sesiones(app, como):
    c = como("vendedor")
    r = c.post("/auth/cambiar-password", data={"actual": "Vende1234", "password": "Nueva1234", "password2": "Nueva1234"})
    assert r.status_code == 302
    assert c.get("/").status_code == 200  # la sesión actual sigue
    otro = app.test_client()
    assert otro.post("/auth/login", data={"usuario": "vendedor", "password": "Vende1234"}).status_code == 200  # vieja ya no


def test_registro_inicial_solo_sin_usuarios(client):
    r = client.get("/auth/registro-inicial")
    assert r.status_code == 302


def test_xss_escapado(como):
    c = como("admin")
    c.post("/clientes/nuevo", data={"nombre": "<script>alert(1)</script>", "apellido": "X"})
    html = c.get("/clientes/?q=script").get_data(as_text=True)
    assert "<script>alert(1)</script>" not in html and "&lt;script&gt;" in html
