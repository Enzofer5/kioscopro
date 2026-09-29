# KioscoPro — Sistema de gestión para kiosco / drugstore

Aplicación web completa para el mostrador: punto de venta con lector de código de barras, productos, stock,
compras, proveedores, clientes, caja con arqueo, gastos, empleados, usuarios con roles y reportes con gráficos.

- **Backend:** Python 3.10+ · Flask 3 · SQLAlchemy 2 (arquitectura en capas: rutas → servicios → modelos)
- **Base de datos:** MySQL 8.0.16+ / MariaDB 10.6+ (script completo en `database/schema.sql`)
- **Frontend:** HTML5 + CSS3 + JavaScript sin frameworks · Chart.js (local, funciona sin internet)
- **Responsive:** se usa desde la PC del mostrador y desde el celular

> El análisis de requisitos, la arquitectura, el modelo de datos y las relaciones están en
> [`docs/ARQUITECTURA.md`](docs/ARQUITECTURA.md).

---

## 1. Probarlo YA (modo demo, sin instalar MySQL) — Windows

1. Instalá Python desde <https://www.python.org/downloads/> (tildá **"Add python.exe to PATH"**).
2. Doble clic en **`INICIAR.bat`**.
3. La primera vez instala las dependencias, crea una base SQLite de prueba con 45 días de ventas y abre el navegador
   en http://127.0.0.1:5050. El sistema queda funcionando **en segundo plano** (aunque se cierre la ventana negra).
4. Para apagarlo: doble clic en **`DETENER.bat`**. Si algo falla, el registro está en `instance/servidor.log`.

| Usuario | Contraseña | Rol |
|---|---|---|
| `dueno` | `Dueno1234` | Dueño (todo) |
| `admin` | `Admin1234` | Administrador |
| `cajero` | `Caja1234` | Cajero (POS + caja) |
| `vendedor` | `Vende1234` | Vendedor (solo POS, productos, clientes) |

Para empezar la demo de cero: borrá la carpeta `instance` y el archivo `.env`, y volvé a ejecutar `INICIAR.bat`.

---

## 2. Instalación con MySQL (uso real)

### 2.1 Requisitos
- Python 3.10 o superior
- MySQL 8.0.16+ o MariaDB 10.6+ (necesarios para que los `CHECK` se apliquen)

### 2.2 Crear la base de datos

```bash
mysql -u root -p < database/schema.sql
```

Luego creá un usuario exclusivo para la aplicación (no uses root):

```sql
CREATE USER 'kiosco'@'localhost' IDENTIFIED BY 'una-clave-segura';
GRANT SELECT, INSERT, UPDATE, DELETE ON kiosco_db.* TO 'kiosco'@'localhost';
FLUSH PRIVILEGES;
```

> ⚠️ `schema.sql` **borra y recrea** las tablas (`DROP TABLE IF EXISTS`). Ejecutalo solo en la instalación inicial.

### 2.3 Instalar la aplicación

**Windows (PowerShell / CMD)**
```bat
cd drugstore
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

**Linux / macOS**
```bash
cd drugstore
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Editá `.env`: completá `DB_USER`, `DB_PASSWORD`, `NEGOCIO_NOMBRE` y generá una `SECRET_KEY`:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

### 2.4 Iniciar

```bash
flask init-db        # verifica/crea tablas y datos base (seguro de ejecutar varias veces)
python run.py        # http://127.0.0.1:5050
```

La primera vez aparece la pantalla **"Creá la cuenta del dueño"**. Después el dueño crea los usuarios del equipo
desde *Usuarios*.

**Datos de prueba en MySQL (opcional):** sobre una base recién creada (sin usuarios) ejecutá `flask seed-demo`.

### 2.5 Usarlo desde el celular
En `.env` poné `HOST=0.0.0.0`, reiniciá y desde el celular (misma red Wi-Fi) entrá a `http://IP-DE-LA-PC:5050`.
Con `HOST=0.0.0.0` la app arranca automáticamente con **Waitress** (servidor de producción) y nunca expone el
depurador de Flask. Puede que Windows pida permitir el acceso en el firewall.

---

## 3. Despliegue en un servidor

1. `APP_ENV=production`, `SECRET_KEY` real, `SESSION_COOKIE_SECURE=1`, `BEHIND_PROXY=1`.
2. Servidor WSGI:
   - Linux: `gunicorn -w 3 -b 127.0.0.1:8000 wsgi:app`
   - Windows: `waitress-serve --listen=127.0.0.1:8000 wsgi:app`
3. Nginx (o Apache/Caddy) delante con HTTPS, sirviendo `/static` directamente:

```nginx
server {
    server_name kiosco.midominio.com;
    client_max_body_size 5M;
    location /static/ { alias /ruta/drugstore/app/static/; expires 7d; }
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

4. Backups diarios: `mysqldump -u root -p kiosco_db > backup_$(date +%F).sql`
5. Configurá `MAIL_*` y `APP_URL` para que funcione la recuperación de contraseña por email.

> El limitador de intentos de login guarda los contadores en memoria de cada proceso. Con varios workers de
> gunicorn cada uno cuenta por separado; para instalaciones grandes conviene moverlo a Redis.

---

## 4. Comandos útiles

| Comando | Qué hace |
|---|---|
| `flask init-db` | Crea tablas faltantes y carga roles, permisos, métodos de pago, unidades y categorías |
| `flask seed-demo` | Carga usuarios, productos, compras, ventas y gastos de ejemplo (solo en base vacía) |
| `flask reset-password USUARIO` | Cambia la contraseña de un usuario desde el servidor (si el dueño pierde el acceso) |
| `pip install -r requirements-dev.txt && pytest` | Ejecuta las pruebas automatizadas |

---

## 5. Roles y permisos

| Permiso | Dueño | Administrador | Cajero | Vendedor |
|---|:-:|:-:|:-:|:-:|
| Punto de venta | ✔ | ✔ | ✔ | ✔ |
| Ver productos, stock y alertas | ✔ | ✔ | ✔ | ✔ |
| Clientes (consultar / alta) | ✔ | ✔ | ✔ | ✔ |
| Abrir, operar y cerrar caja | ✔ | ✔ | ✔ | — |
| Montos, ganancias y gráficos del dashboard | ✔ | ✔ | — | — |
| ABM productos / categorías / marcas / precios | ✔ | ✔ | — | — |
| Ajustes de stock, compras, proveedores | ✔ | ✔ | — | — |
| Historial de ventas, anulaciones y devoluciones | ✔ | ✔ | — | — |
| Gastos, reportes, cierres anteriores | ✔ | ✔ | — | — |
| Empleados y usuarios | ✔ | ✔ (no puede tocar al dueño) | — | — |

Los permisos son datos (tablas `permisos` y `rol_permisos`); cada ruta se protege con
`@permiso_requerido("codigo")`. Un vendedor que intenta abrir una URL administrativa recibe **403**, y la API del
POS no le envía el costo de los productos.

---

## 6. Uso rápido del punto de venta

| Tecla | Acción |
|---|---|
| **F9** (desde cualquier pantalla) | Ir a Nueva venta |
| **F2** | Foco en el buscador |
| Escanear / escribir + **Enter** | Agrega el producto (coincidencia exacta de código o resultado resaltado) |
| `3*` + código | Agrega 3 unidades de ese código |
| **↑ / ↓** | Moverse entre resultados |
| **F4** o Enter con el buscador vacío | Cobrar |
| **Esc** | Limpiar la búsqueda |

- Descuento por ítem (%) y descuento general (% o $).
- En efectivo: botones de billetes sugeridos y cálculo de vuelto.
- Al confirmar: se registra venta, detalle, pago, movimiento de stock y de caja en **una sola transacción**, y se
  ofrece imprimir el comprobante (formato ticket 80 mm).
- El carrito se conserva si se recarga la página por error.

---

## 7. Reglas de negocio importantes

- **Caja:** solo puede haber una caja abierta (garantizado por un índice `UNIQUE` en la base). Sin caja abierta no
  se puede vender (`REQUIERE_CAJA_ABIERTA=1`).
  *Dinero esperado = inicial + ventas en efectivo + ingresos − egresos − retiros − gastos de caja − devoluciones en efectivo.*
- **Stock:** nunca queda negativo (validación en el servicio + `CHECK` en MySQL). Cada cambio queda en
  `movimientos_stock` con stock anterior, nuevo, usuario, fecha y motivo. El stock no se edita desde la ficha del
  producto: se mueve desde *Stock* o *Compras* para no perder trazabilidad.
- **Anulaciones:** las ventas nunca se borran. Pasan a *Anulada* (error de carga, siempre reintegra stock) o
  *Devuelta* (se puede elegir si la mercadería vuelve al stock). Se guarda quién, cuándo y por qué, y se registra la
  salida de dinero en la caja abierta con el mismo medio de pago.
- **Ganancia:** se calcula con el precio de compra **congelado en cada línea de venta**, por lo que cambiar un costo
  hoy no altera la ganancia de ventas pasadas. Ganancia neta = bruta − gastos.
- **Compras:** suman stock y, si se tilda "Actualizar costos", actualizan el precio de compra del producto. No se
  permite cargar dos veces el mismo comprobante del mismo proveedor.
- **Listados:** productos, ventas, compras, clientes, proveedores y movimientos no se cargan completos: primero se
  filtra (hay accesos rápidos como "Todos los activos" o "Ventas de hoy").

---

## 8. Seguridad implementada

| Medida | Dónde |
|---|---|
| Contraseñas con hash **scrypt** (nunca en texto plano) | `models/seguridad.py` |
| Sesiones firmadas, cookies `HttpOnly` + `SameSite=Lax` (+ `Secure` en producción) | `config.py` |
| Cambiar la contraseña o desactivar un usuario **cierra sus otras sesiones** (`version_sesion`) | `Usuario.get_id` |
| Protección **CSRF** en todos los formularios y en las llamadas `fetch` | Flask-WTF + `static/js/app.js` |
| Consultas parametrizadas vía SQLAlchemy (sin SQL concatenado) → sin SQL Injection | `services/` |
| **XSS:** autoescape de Jinja, JS que usa `textContent`/`KP.esc`, y **CSP** sin scripts inline | `app/__init__.py` |
| Cabeceras `X-Frame-Options`, `nosniff`, `Referrer-Policy`, `Cache-Control: no-store` | `app/__init__.py` |
| Límite de intentos de login y de pedidos de recuperación | `utils/rate_limit.py` |
| Tokens de recuperación de un solo uso, 1 hora, guardados como SHA-256 | `services/auth_service.py` |
| Respuesta uniforme en recuperación (no revela qué emails existen) | idem |
| Redirecciones `next` solo a rutas internas | `routes/auth.py` |
| Precios recalculados en el servidor (el navegador no puede alterar un total) | `services/venta_service.py` |
| Bloqueo de filas (`SELECT … FOR UPDATE`) al descontar stock y operar caja | `services/stock_service.py` |
| Imágenes re-procesadas con Pillow a WEBP con nombre aleatorio | `utils/imagenes.py` |
| Contraseñas temporales obligan a cambiarlas al ingresar | `app/__init__.py` |
| Secretos en `.env` (fuera del repositorio) | `.env.example`, `.gitignore` |

---

## 9. Estructura

```
drugstore/
├── run.py · wsgi.py · INICIAR.bat · requirements.txt · .env.example · .flaskenv
├── database/schema.sql          Script MySQL completo (tablas + datos base)
├── docs/ARQUITECTURA.md         Análisis, arquitectura, DER y decisiones
├── tests/                       Pruebas de permisos, POS, caja, compras, anulaciones, XSS
└── app/
    ├── __init__.py              App factory, seguridad, errores
    ├── config.py · extensions.py · cli.py
    ├── models/                  seguridad · personas · catalogo · ventas · operaciones
    ├── services/                auth · usuario · personas · producto · stock · venta · compra · caja · gasto · reporte
    ├── routes/                  auth · dashboard · ventas · productos · stock · compras · proveedores · clientes
    │                            caja · gastos · empleados · usuarios · reportes
    ├── utils/                   decorators · helpers · rate_limit · mailer · imagenes
    ├── templates/               base.html + una carpeta por módulo + partials/ + errors/
    └── static/                  css/app.css · js/(app, pos, compras, stock, caja, charts…) · img/ · uploads/
```

## 10. Solución de problemas

| Problema | Solución |
|---|---|
| `Base de datos no disponible` | Revisá `DB_*` en `.env`, que MySQL esté iniciado y ejecutá `flask init-db`. |
| `Access denied for user` | Usuario/clave de MySQL incorrectos o faltan permisos sobre `kiosco_db`. |
| `cryptography is required` | `pip install -r requirements.txt` (MySQL 8 usa `caching_sha2_password`). |
| No carga desde el celular | `HOST=0.0.0.0`, misma red Wi-Fi, permitir Python en el firewall de Windows. |
| Se perdió la clave del dueño | `flask reset-password dueno` en la PC donde corre el sistema. |
| Las sesiones se cierran al reiniciar | Falta `SECRET_KEY` fija en `.env`. |

Íconos: [Lucide](https://lucide.dev) (ISC). Gráficos: [Chart.js](https://www.chartjs.org) (MIT).
