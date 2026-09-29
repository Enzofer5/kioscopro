"""Comandos de consola:
    flask init-db          crea las tablas (si no existen) y carga los datos base
    flask seed-demo        carga usuarios, productos y ventas de ejemplo
    flask reset-password   restablece la contraseña de un usuario desde el servidor
"""
import random
from datetime import timedelta
from decimal import Decimal

import click
from sqlalchemy import select

from .extensions import db
from .models import (
    PERMISOS,
    ROL_ADMIN,
    ROL_CAJERO,
    ROL_DUENO,
    ROL_VENDEDOR,
    ROLES,
    Caja,
    Categoria,
    CategoriaGasto,
    Cliente,
    Compra,
    DetalleCompra,
    DetalleVenta,
    Empleado,
    Gasto,
    Marca,
    MetodoPago,
    MovimientoCaja,
    MovimientoStock,
    Pago,
    Permiso,
    Producto,
    Proveedor,
    Rol,
    UnidadMedida,
    Usuario,
    Venta,
)
from .utils.helpers import ahora, redondear

METODOS_PAGO = [
    ("efectivo", "Efectivo", True, 1),
    ("transferencia", "Transferencia", False, 2),
    ("debito", "Débito", False, 3),
    ("credito", "Crédito", False, 4),
    ("mercadopago", "Mercado Pago", False, 5),
    ("otro", "Otro", False, 6),
]
UNIDADES = [("Unidad", "u", False), ("Paquete", "paq", False), ("Caja", "cja", False),
            ("Kilogramo", "kg", True), ("Litro", "l", True), ("Gramo", "g", True)]
CATEGORIAS = ["Bebidas", "Cervezas", "Aguas", "Galletitas", "Alfajores", "Chocolates", "Cigarrillos",
              "Golosinas", "Snacks", "Limpieza", "Perfumería", "Varios"]
CATEGORIAS_GASTO = ["Alquiler", "Luz", "Internet", "Proveedores", "Limpieza", "Mantenimiento", "Sueldos", "Impuestos", "Otros"]


def cargar_datos_base():
    """Idempotente: solo inserta lo que falta."""
    permisos = {}
    for codigo, desc in PERMISOS.items():
        p = db.session.scalar(select(Permiso).where(Permiso.codigo == codigo))
        if p is None:
            p = Permiso(codigo=codigo, descripcion=desc)
            db.session.add(p)
        permisos[codigo] = p
    for nombre, (desc, codigos) in ROLES.items():
        rol = db.session.scalar(select(Rol).where(Rol.nombre == nombre))
        if rol is None:
            rol = Rol(nombre=nombre, descripcion=desc)
            db.session.add(rol)
        rol.permisos = [permisos[c] for c in codigos]
    for codigo, nombre, efectivo, orden in METODOS_PAGO:
        if not db.session.scalar(select(MetodoPago).where(MetodoPago.codigo == codigo)):
            db.session.add(MetodoPago(codigo=codigo, nombre=nombre, es_efectivo=efectivo, orden=orden, activo=True))
    for nombre, abrev, dec in UNIDADES:
        if not db.session.scalar(select(UnidadMedida).where(UnidadMedida.nombre == nombre)):
            db.session.add(UnidadMedida(nombre=nombre, abreviatura=abrev, permite_decimales=dec))
    for nombre in CATEGORIAS:
        if not db.session.scalar(select(Categoria).where(Categoria.nombre == nombre)):
            db.session.add(Categoria(nombre=nombre, activo=True))
    for nombre in CATEGORIAS_GASTO:
        if not db.session.scalar(select(CategoriaGasto).where(CategoriaGasto.nombre == nombre)):
            db.session.add(CategoriaGasto(nombre=nombre, activo=True))
    db.session.commit()


# (nombre, categoría, marca, código, costo, venta, stock, mínimo)
PRODUCTOS_DEMO = [
    ("Coca Cola 500 ml", "Bebidas", "Coca-Cola", "7790895000997", 720, 1100, 48, 12),
    ("Coca Cola 1,5 L", "Bebidas", "Coca-Cola", "7790895001413", 1350, 2100, 24, 8),
    ("Coca Cola Zero 500 ml", "Bebidas", "Coca-Cola", "7790895067556", 720, 1100, 6, 10),
    ("Pepsi 500 ml", "Bebidas", "Pepsi", "7791813421665", 620, 950, 30, 10),
    ("Pepsi 1,5 L", "Bebidas", "Pepsi", "7791813423232", 1150, 1800, 0, 6),
    ("Sprite 500 ml", "Bebidas", "Coca-Cola", "7790895000430", 700, 1050, 20, 8),
    ("Agua Villavicencio 500 ml", "Aguas", "Villavicencio", "7798062548679", 450, 750, 40, 12),
    ("Agua Villavicencio 1,5 L", "Aguas", "Villavicencio", "7798062540253", 750, 1200, 18, 6),
    ("Agua saborizada Levité Pomelo 500 ml", "Aguas", "Villavicencio", "7798062548877", 600, 950, 15, 6),
    ("Cerveza Quilmes lata 473 ml", "Cervezas", "Quilmes", "7792798007394", 900, 1450, 60, 24),
    ("Cerveza Brahma lata 473 ml", "Cervezas", "Brahma", "7792798012053", 850, 1350, 3, 12),
    ("Cerveza Stella Artois 330 ml", "Cervezas", "Stella Artois", "7792798010011", 1100, 1700, 24, 12),
    ("Galletitas Oreo 118 g", "Galletitas", "Terrabusi", "7622300489434", 650, 1050, 25, 8),
    ("Galletitas Criollitas 169 g", "Galletitas", "Bagley", "7790040133488", 500, 850, 20, 8),
    ("Galletitas Chocolinas 170 g", "Galletitas", "Bagley", "7790040613706", 700, 1150, 0, 6),
    ("Alfajor Jorgito chocolate", "Alfajores", "Jorgito", "7790957000224", 380, 650, 50, 20),
    ("Alfajor Guaymallén dulce de leche", "Alfajores", "Guaymallén", "7797394000017", 180, 350, 80, 30),
    ("Alfajor Havanna chocolate", "Alfajores", "Havanna", "7790569000124", 1100, 1800, 12, 6),
    ("Alfajor Tatín triple", "Alfajores", "Arcor", "7790580120023", 250, 450, 9, 20),
    ("Chocolate Milka 55 g", "Chocolates", "Milka", "7622300840327", 900, 1450, 20, 8),
    ("Chocolate Cofler Block 38 g", "Chocolates", "Arcor", "7790580660000", 700, 1100, 18, 8),
    ("Chocolate Águila 150 g", "Chocolates", "Arcor", "7790580104108", 1600, 2500, 5, 4),
    ("Cigarrillos Marlboro Box 20", "Cigarrillos", "Marlboro", "7798158780014", 2600, 3200, 40, 20),
    ("Cigarrillos Philip Morris Box 20", "Cigarrillos", "Philip Morris", "7798158780212", 2300, 2850, 35, 20),
    ("Cigarrillos Lucky Strike 20", "Cigarrillos", "Lucky Strike", "7791240001024", 2400, 2950, 0, 10),
    ("Chicles Beldent menta", "Golosinas", "Arcor", "7790580413309", 250, 450, 60, 20),
    ("Caramelos Sugus x 10", "Golosinas", "Arcor", "7790580590108", 150, 300, 45, 15),
    ("Pastillas Halls mentol", "Golosinas", "Halls", "7622300106416", 300, 550, 30, 10),
    ("Papas Lay's clásicas 85 g", "Snacks", "Lay's", "7790310981054", 900, 1450, 22, 8),
    ("Palitos Pehuamar 100 g", "Snacks", "Pehuamar", "7790310002551", 600, 1000, 16, 6),
    ("Maní salado Pehuamar 120 g", "Snacks", "Pehuamar", "7790310001240", 550, 900, 4, 6),
    ("Lavandina Ayudín 1 L", "Limpieza", "Ayudín", "7793253005672", 650, 1100, 12, 4),
    ("Detergente Magistral 300 ml", "Limpieza", "Magistral", "7500435126373", 900, 1500, 10, 4),
    ("Jabón Dove 90 g", "Perfumería", "Dove", "7791293022626", 850, 1400, 8, 4),
    ("Pilas Duracell AA x2", "Varios", "Duracell", "0041333424012", 2200, 3400, 10, 4),
    ("Encendedor Bic", "Varios", "Bic", "0070330705159", 700, 1200, 25, 10),
    ("Caramelos a granel", "Golosinas", None, "", 6000, 10000, Decimal("2.5"), 1),
]


def _cargar_demo(dias=45):
    ahora_ = ahora()
    roles = {r.nombre: r for r in db.session.scalars(select(Rol)).all()}
    usuarios_demo = [
        ("dueno", "dueno@demo.com", "Carlos", "Pereyra", ROL_DUENO, "Dueno1234", None),
        ("admin", "admin@demo.com", "Laura", "Gómez", ROL_ADMIN, "Admin1234", ("30111222", "Encargada")),
        ("vendedor", "vendedor@demo.com", "Martín", "Suárez", ROL_VENDEDOR, "Vende1234", ("35111222", "Vendedor")),
        ("cajero", "cajero@demo.com", "Sofía", "Ramírez", ROL_CAJERO, "Caja1234", ("38111222", "Cajera")),
    ]
    usuarios = {}
    for username, email, nombre, apellido, rol, clave, emp in usuarios_demo:
        empleado = None
        if emp:
            empleado = Empleado(nombre=nombre, apellido=apellido, dni=emp[0], puesto=emp[1], telefono="11 5555-0000",
                                email=email, fecha_ingreso=(ahora_ - timedelta(days=400)).date(), activo=True, creado_en=ahora_)
            db.session.add(empleado)
        u = Usuario(username=username, email=email, nombre=nombre, apellido=apellido, rol=roles[rol],
                    empleado=empleado, activo=True, creado_en=ahora_)
        u.set_password(clave)
        db.session.add(u)
        usuarios[username] = u
    db.session.add(Empleado(nombre="Diego", apellido="Fernández", dni="40111222", puesto="Repositor",
                            fecha_ingreso=(ahora_ - timedelta(days=90)).date(), activo=True, creado_en=ahora_))

    marcas = {}
    categorias = {c.nombre: c for c in db.session.scalars(select(Categoria)).all()}
    unidades = {u.abreviatura: u for u in db.session.scalars(select(UnidadMedida)).all()}
    productos = []
    for nombre, cat, marca, codigo, costo, venta, stock, minimo in PRODUCTOS_DEMO:
        if marca and marca not in marcas:
            marcas[marca] = Marca(nombre=marca, activo=True)
            db.session.add(marcas[marca])
        p = Producto(nombre=nombre, categoria=categorias[cat], marca=marcas.get(marca), codigo_barras=codigo or None,
                     unidad=unidades["kg" if "granel" in nombre else "u"], precio_compra=costo, precio_venta=venta,
                     stock_actual=0, stock_minimo=minimo, activo=True, creado_en=ahora_, actualizado_en=ahora_)
        db.session.add(p)
        productos.append((p, Decimal(stock)))

    proveedores = [
        Proveedor(razon_social="Distribuidora Norte S.A.", cuit="30-71234567-1", telefono="11 4000-1000",
                  email="ventas@distnorte.com.ar", contacto="Jorge", activo=True, creado_en=ahora_),
        Proveedor(razon_social="Golosinas del Sur SRL", cuit="30-70987654-4", telefono="11 4000-2000",
                  contacto="Marta", activo=True, creado_en=ahora_),
    ]
    db.session.add_all(proveedores)
    clientes = [
        Cliente(nombre="Juan", apellido="López", dni="28123456", telefono="11 6000-1111", fecha_registro=ahora_, activo=True),
        Cliente(nombre="María", apellido="García", dni="31987654", email="maria@example.com", fecha_registro=ahora_, activo=True),
        Cliente(nombre="Pedro", apellido="Martínez", fecha_registro=ahora_, activo=True),
    ]
    db.session.add_all(clientes)
    db.session.flush()

    dueno = usuarios["dueno"]
    rnd = random.Random(42)
    inicio = (ahora_ - timedelta(days=dias)).replace(hour=8, minute=0, second=0)

    # Compra inicial: stock suficiente para toda la historia + el stock final deseado
    compra = Compra(proveedor_id=proveedores[0].id, usuario_id=dueno.id, fecha=inicio.date(),
                    numero_comprobante="0001-00000001", total=0, creado_en=inicio)
    db.session.add(compra)
    db.session.flush()
    stock_mov = {}
    total_compra = Decimal(0)
    for p, _ in productos:
        cant = Decimal(400 if p.unidad.abreviatura == "u" else 20)
        sub = redondear(cant * p.precio_compra)
        total_compra += sub
        db.session.add(DetalleCompra(compra_id=compra.id, producto_id=p.id, cantidad=cant, precio_unitario=p.precio_compra, subtotal=sub))
        db.session.add(MovimientoStock(producto_id=p.id, tipo="compra", cantidad=cant, stock_anterior=0, stock_nuevo=cant,
                                       motivo=f"Compra #{compra.id} - {proveedores[0].razon_social}", usuario_id=dueno.id,
                                       compra_id=compra.id, fecha=inicio))
        stock_mov[p.id] = cant
    compra.total = total_compra

    metodos = {m.codigo: m for m in db.session.scalars(select(MetodoPago)).all()}
    pesos_metodo = [("efectivo", 50), ("mercadopago", 20), ("debito", 15), ("transferencia", 10), ("credito", 5)]
    vendedores = [usuarios["cajero"], usuarios["vendedor"], usuarios["admin"]]
    unitarios = [p for p, _ in productos if p.unidad.abreviatura == "u"]

    for dia in range(dias, 0, -1):
        fecha_dia = (ahora_ - timedelta(days=dia)).replace(hour=8, minute=0, second=0)
        caja = Caja(usuario_apertura_id=usuarios["cajero"].id, fecha_apertura=fecha_dia, monto_inicial=20000, abierta=True)
        db.session.add(caja)
        db.session.flush()
        efectivo = Decimal(20000)
        for _ in range(rnd.randint(14, 32)):
            momento = fecha_dia + timedelta(minutes=rnd.randint(10, 780))
            items = rnd.sample(unitarios, rnd.randint(1, 4))
            vendedor = rnd.choice(vendedores)
            metodo = metodos[rnd.choices([m for m, _ in pesos_metodo], [w for _, w in pesos_metodo])[0]]
            venta = Venta(fecha=momento, usuario_id=vendedor.id, caja_id=caja.id, subtotal=0, descuento=0, total=0,
                          estado="completada", cliente_id=rnd.choice([None, None, None, clientes[0].id, clientes[1].id]))
            db.session.add(venta)
            db.session.flush()
            total = Decimal(0)
            for p in items:
                cant = Decimal(rnd.choice([1, 1, 1, 2, 3]))
                if stock_mov[p.id] - cant < 60:
                    continue
                sub = redondear(cant * p.precio_venta)
                total += sub
                db.session.add(DetalleVenta(venta_id=venta.id, producto_id=p.id, cantidad=cant, precio_unitario=p.precio_venta,
                                            costo_unitario=p.precio_compra, descuento=0, subtotal=sub))
                db.session.add(MovimientoStock(producto_id=p.id, tipo="venta", cantidad=-cant, stock_anterior=stock_mov[p.id],
                                               stock_nuevo=stock_mov[p.id] - cant, motivo=f"Venta #{venta.id}",
                                               usuario_id=vendedor.id, venta_id=venta.id, fecha=momento))
                stock_mov[p.id] -= cant
            if total == 0:
                db.session.delete(venta)
                db.session.flush()
                continue
            venta.subtotal = venta.total = total
            db.session.add(Pago(venta_id=venta.id, metodo_pago_id=metodo.id, monto=total))
            db.session.add(MovimientoCaja(caja_id=caja.id, tipo="venta", concepto=f"Venta #{venta.id}", monto=total,
                                          metodo_pago_id=metodo.id, usuario_id=vendedor.id, venta_id=venta.id, fecha=momento))
            if metodo.es_efectivo:
                efectivo += total
        retiro = redondear((efectivo - 20000) * Decimal("0.8"))
        if retiro > 0:
            db.session.add(MovimientoCaja(caja_id=caja.id, tipo="retiro", concepto="Retiro para depósito", monto=retiro,
                                          metodo_pago_id=metodos["efectivo"].id, usuario_id=dueno.id,
                                          fecha=fecha_dia + timedelta(hours=13)))
            efectivo -= retiro
        caja.monto_esperado = efectivo
        caja.monto_declarado = efectivo - rnd.choice([0, 0, 0, 50, 100, -100])
        caja.diferencia = caja.monto_declarado - efectivo
        caja.fecha_cierre = fecha_dia + timedelta(hours=13, minutes=30)
        caja.usuario_cierre_id = usuarios["cajero"].id
        caja.abierta = None

    # Gastos mensuales de ejemplo
    cats = {c.nombre: c for c in db.session.scalars(select(CategoriaGasto)).all()}
    for i, (cat, desc, monto) in enumerate([("Alquiler", "Alquiler del local", 350000), ("Luz", "Factura Edenor", 48000),
                                            ("Internet", "Fibra óptica", 22000), ("Limpieza", "Artículos de limpieza", 9000)]):
        for mes in (0, 1):
            f = (ahora_.replace(day=1) - timedelta(days=30 * mes)).date().replace(day=5 + i)
            if f <= ahora_.date():
                db.session.add(Gasto(categoria_id=cats[cat].id, descripcion=desc, monto=monto, metodo_pago_id=metodos["transferencia"].id,
                                     fecha=f, usuario_id=dueno.id, creado_en=ahora_))

    # Ajuste final para dejar el stock "deseado" del catálogo (genera alertas de ejemplo)
    for p, deseado in productos:
        actual = stock_mov[p.id]
        if actual != deseado:
            db.session.add(MovimientoStock(producto_id=p.id, tipo="ajuste", cantidad=deseado - actual, stock_anterior=actual,
                                           stock_nuevo=deseado, motivo="Ajuste por inventario (datos de ejemplo)",
                                           usuario_id=dueno.id, fecha=ahora_ - timedelta(hours=2)))
        p.stock_actual = deseado
    db.session.commit()


def registrar_comandos(app):
    @app.cli.command("init-db")
    def init_db():
        """Crea las tablas que falten y carga roles, permisos, métodos de pago, unidades y categorías."""
        db.create_all()
        cargar_datos_base()
        click.echo("Base de datos lista. Ingresá a la app para registrar al dueño.")

    @app.cli.command("seed-demo")
    @click.option("--dias", default=45, help="Días de historial de ventas a generar")
    def seed_demo(dias):
        """Carga datos de ejemplo (solo en una base vacía)."""
        db.create_all()
        cargar_datos_base()
        if db.session.scalar(select(Usuario.id).limit(1)):
            click.echo("La base ya tiene usuarios: no se cargan datos de ejemplo.")
            return
        _cargar_demo(dias)
        click.echo("Datos de ejemplo cargados.\n  dueno / Dueno1234\n  admin / Admin1234\n  vendedor / Vende1234\n  cajero / Caja1234")

    @app.cli.command("reset-password")
    @click.argument("username")
    @click.password_option()
    def reset_password(username, password):
        """Cambia la contraseña de un usuario (por si el dueño pierde el acceso)."""
        from .services import ErrorNegocio
        from .services.auth_service import validar_password

        usuario = db.session.scalar(select(Usuario).where(Usuario.username == username.lower()))
        if usuario is None:
            raise click.ClickException("Usuario inexistente.")
        try:
            validar_password(password)
        except ErrorNegocio as exc:
            raise click.ClickException(str(exc)) from exc
        usuario.set_password(password)
        usuario.activo = True
        db.session.commit()
        click.echo("Contraseña actualizada.")
