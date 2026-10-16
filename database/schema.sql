-- =============================================================================
-- KioscoPro - Sistema de gestión para kiosco / drugstore
-- Script completo de creación de la base de datos MySQL 8.0.16+ / MariaDB 10.6+
--
-- Uso:   mysql -u root -p < database/schema.sql
-- Crea la base, las tablas (3FN, PK, FK, UNIQUE, CHECK, índices) y carga los
-- datos base: roles, permisos, métodos de pago, unidades y categorías.
-- Los usuarios NO se crean aquí: el dueño se registra desde la aplicación
-- (o ejecutá 'flask seed-demo' sobre una base vacía para datos de prueba).
-- =============================================================================

CREATE DATABASE IF NOT EXISTS kiosco_db
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE kiosco_db;

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

DROP TABLE IF EXISTS pagos;
DROP TABLE IF EXISTS movimientos_stock;
DROP TABLE IF EXISTS movimientos_caja;
DROP TABLE IF EXISTS detalle_ventas;
DROP TABLE IF EXISTS anulaciones_venta;
DROP TABLE IF EXISTS ventas;
DROP TABLE IF EXISTS detalle_compras;
DROP TABLE IF EXISTS password_resets;
DROP TABLE IF EXISTS gastos;
DROP TABLE IF EXISTS compras;
DROP TABLE IF EXISTS cajas;
DROP TABLE IF EXISTS usuarios;
DROP TABLE IF EXISTS rol_permisos;
DROP TABLE IF EXISTS productos;
DROP TABLE IF EXISTS unidades_medida;
DROP TABLE IF EXISTS roles;
DROP TABLE IF EXISTS proveedores;
DROP TABLE IF EXISTS permisos;
DROP TABLE IF EXISTS metodos_pago;
DROP TABLE IF EXISTS marcas;
DROP TABLE IF EXISTS empleados;
DROP TABLE IF EXISTS clientes;
DROP TABLE IF EXISTS categorias_gasto;
DROP TABLE IF EXISTS categorias;
SET FOREIGN_KEY_CHECKS = 1;

-- -----------------------------------------------------------------------------
-- categorias: Categorías de productos
-- -----------------------------------------------------------------------------
CREATE TABLE categorias (
    id INTEGER NOT NULL AUTO_INCREMENT,
    nombre VARCHAR(60) NOT NULL,
    activo BOOL NOT NULL,
    CONSTRAINT pk_categorias PRIMARY KEY (id),
    CONSTRAINT uq_categorias_nombre UNIQUE (nombre)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Categorías de productos';

-- -----------------------------------------------------------------------------
-- categorias_gasto: Categorías de gastos
-- -----------------------------------------------------------------------------
CREATE TABLE categorias_gasto (
    id INTEGER NOT NULL AUTO_INCREMENT,
    nombre VARCHAR(60) NOT NULL,
    activo BOOL NOT NULL,
    CONSTRAINT pk_categorias_gasto PRIMARY KEY (id),
    CONSTRAINT uq_categorias_gasto_nombre UNIQUE (nombre)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Categorías de gastos';

-- -----------------------------------------------------------------------------
-- clientes: Clientes (opcionales en la venta)
-- -----------------------------------------------------------------------------
CREATE TABLE clientes (
    id INTEGER NOT NULL AUTO_INCREMENT,
    nombre VARCHAR(80) NOT NULL,
    apellido VARCHAR(80) NOT NULL,
    dni VARCHAR(15),
    telefono VARCHAR(30),
    email VARCHAR(120),
    direccion VARCHAR(200),
    fecha_registro DATETIME NOT NULL,
    activo BOOL NOT NULL,
    CONSTRAINT pk_clientes PRIMARY KEY (id),
    CONSTRAINT uq_clientes_dni UNIQUE (dni)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Clientes (opcionales en la venta)';
CREATE INDEX ix_clientes_apellido_nombre ON clientes (apellido, nombre);

-- -----------------------------------------------------------------------------
-- empleados: Personal del negocio (puede o no tener usuario)
-- -----------------------------------------------------------------------------
CREATE TABLE empleados (
    id INTEGER NOT NULL AUTO_INCREMENT,
    nombre VARCHAR(80) NOT NULL,
    apellido VARCHAR(80) NOT NULL,
    dni VARCHAR(15) NOT NULL,
    telefono VARCHAR(30),
    email VARCHAR(120),
    puesto VARCHAR(60) NOT NULL,
    fecha_ingreso DATE NOT NULL,
    activo BOOL NOT NULL,
    creado_en DATETIME NOT NULL,
    CONSTRAINT pk_empleados PRIMARY KEY (id),
    CONSTRAINT uq_empleados_dni UNIQUE (dni)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Personal del negocio (puede o no tener usuario)';
CREATE INDEX ix_empleados_apellido_nombre ON empleados (apellido, nombre);

-- -----------------------------------------------------------------------------
-- marcas: Marcas de productos
-- -----------------------------------------------------------------------------
CREATE TABLE marcas (
    id INTEGER NOT NULL AUTO_INCREMENT,
    nombre VARCHAR(60) NOT NULL,
    activo BOOL NOT NULL,
    CONSTRAINT pk_marcas PRIMARY KEY (id),
    CONSTRAINT uq_marcas_nombre UNIQUE (nombre)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Marcas de productos';

-- -----------------------------------------------------------------------------
-- metodos_pago: Medios de pago
-- -----------------------------------------------------------------------------
CREATE TABLE metodos_pago (
    id INTEGER NOT NULL AUTO_INCREMENT,
    codigo VARCHAR(20) NOT NULL,
    nombre VARCHAR(40) NOT NULL,
    es_efectivo BOOL NOT NULL,
    orden SMALLINT NOT NULL,
    activo BOOL NOT NULL,
    CONSTRAINT pk_metodos_pago PRIMARY KEY (id),
    CONSTRAINT uq_metodos_pago_codigo UNIQUE (codigo),
    CONSTRAINT uq_metodos_pago_nombre UNIQUE (nombre)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Medios de pago';

-- -----------------------------------------------------------------------------
-- permisos: Catálogo de permisos granulares
-- -----------------------------------------------------------------------------
CREATE TABLE permisos (
    id INTEGER NOT NULL AUTO_INCREMENT,
    codigo VARCHAR(50) NOT NULL,
    descripcion VARCHAR(150) NOT NULL,
    CONSTRAINT pk_permisos PRIMARY KEY (id),
    CONSTRAINT uq_permisos_codigo UNIQUE (codigo)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Catálogo de permisos granulares';

-- -----------------------------------------------------------------------------
-- proveedores: Proveedores
-- -----------------------------------------------------------------------------
CREATE TABLE proveedores (
    id INTEGER NOT NULL AUTO_INCREMENT,
    razon_social VARCHAR(150) NOT NULL,
    cuit VARCHAR(13),
    telefono VARCHAR(30),
    email VARCHAR(120),
    direccion VARCHAR(200),
    contacto VARCHAR(100),
    activo BOOL NOT NULL,
    observaciones TEXT,
    creado_en DATETIME NOT NULL,
    CONSTRAINT pk_proveedores PRIMARY KEY (id),
    CONSTRAINT uq_proveedores_cuit UNIQUE (cuit)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Proveedores';
CREATE INDEX ix_proveedores_razon_social ON proveedores (razon_social);

-- -----------------------------------------------------------------------------
-- roles: Roles del sistema (Dueño, Administrador, Vendedor, Cajero)
-- -----------------------------------------------------------------------------
CREATE TABLE roles (
    id INTEGER NOT NULL AUTO_INCREMENT,
    nombre VARCHAR(30) NOT NULL,
    descripcion VARCHAR(150),
    CONSTRAINT pk_roles PRIMARY KEY (id),
    CONSTRAINT uq_roles_nombre UNIQUE (nombre)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Roles del sistema (Dueño, Administrador, Vendedor, Cajero)';

-- -----------------------------------------------------------------------------
-- unidades_medida: Unidades de medida
-- -----------------------------------------------------------------------------
CREATE TABLE unidades_medida (
    id INTEGER NOT NULL AUTO_INCREMENT,
    nombre VARCHAR(30) NOT NULL,
    abreviatura VARCHAR(10) NOT NULL,
    permite_decimales BOOL NOT NULL,
    CONSTRAINT pk_unidades_medida PRIMARY KEY (id),
    CONSTRAINT uq_unidades_medida_nombre UNIQUE (nombre),
    CONSTRAINT uq_unidades_medida_abreviatura UNIQUE (abreviatura)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Unidades de medida';

-- -----------------------------------------------------------------------------
-- productos: Catálogo de productos. stock_actual es un saldo que se mantiene junto con movimientos_stock
-- -----------------------------------------------------------------------------
CREATE TABLE productos (
    id INTEGER NOT NULL AUTO_INCREMENT,
    codigo_barras VARCHAR(32),
    nombre VARCHAR(120) NOT NULL,
    descripcion TEXT,
    categoria_id INTEGER NOT NULL,
    marca_id INTEGER,
    unidad_id INTEGER NOT NULL,
    precio_compra NUMERIC(12, 2) NOT NULL,
    precio_venta NUMERIC(12, 2) NOT NULL,
    stock_actual NUMERIC(12, 3) NOT NULL,
    stock_minimo NUMERIC(12, 3) NOT NULL,
    imagen VARCHAR(255),
    activo BOOL NOT NULL,
    creado_en DATETIME NOT NULL,
    actualizado_en DATETIME NOT NULL,
    CONSTRAINT pk_productos PRIMARY KEY (id),
    CONSTRAINT ck_productos_precio_compra_pos CHECK (precio_compra >= 0),
    CONSTRAINT ck_productos_precio_venta_pos CHECK (precio_venta >= 0),
    CONSTRAINT ck_productos_stock_actual_pos CHECK (stock_actual >= 0),
    CONSTRAINT ck_productos_stock_minimo_pos CHECK (stock_minimo >= 0),
    CONSTRAINT uq_productos_codigo_barras UNIQUE (codigo_barras),
    CONSTRAINT fk_productos_categoria_id FOREIGN KEY(categoria_id) REFERENCES categorias (id) ON DELETE RESTRICT,
    CONSTRAINT fk_productos_marca_id FOREIGN KEY(marca_id) REFERENCES marcas (id) ON DELETE RESTRICT,
    CONSTRAINT fk_productos_unidad_id FOREIGN KEY(unidad_id) REFERENCES unidades_medida (id) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Catálogo de productos. stock_actual es un saldo que se mantiene junto con movimientos_stock';
CREATE INDEX ix_productos_activo ON productos (activo);
CREATE INDEX ix_productos_categoria_id ON productos (categoria_id);
CREATE INDEX ix_productos_marca_id ON productos (marca_id);
CREATE INDEX ix_productos_nombre ON productos (nombre);
CREATE INDEX ix_productos_stock ON productos (stock_actual, stock_minimo);

-- -----------------------------------------------------------------------------
-- rol_permisos: Relación N:M entre roles y permisos
-- -----------------------------------------------------------------------------
CREATE TABLE rol_permisos (
    rol_id INTEGER NOT NULL,
    permiso_id INTEGER NOT NULL,
    CONSTRAINT pk_rol_permisos PRIMARY KEY (rol_id, permiso_id),
    CONSTRAINT fk_rol_permisos_rol_id FOREIGN KEY(rol_id) REFERENCES roles (id) ON DELETE CASCADE,
    CONSTRAINT fk_rol_permisos_permiso_id FOREIGN KEY(permiso_id) REFERENCES permisos (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Relación N:M entre roles y permisos';

-- -----------------------------------------------------------------------------
-- usuarios: Cuentas de acceso. password_hash guarda un hash scrypt, nunca la contraseña
-- -----------------------------------------------------------------------------
CREATE TABLE usuarios (
    id INTEGER NOT NULL AUTO_INCREMENT,
    username VARCHAR(40) NOT NULL,
    email VARCHAR(120) NOT NULL,
    nombre VARCHAR(80) NOT NULL,
    apellido VARCHAR(80) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    rol_id INTEGER NOT NULL,
    empleado_id INTEGER,
    activo BOOL NOT NULL,
    debe_cambiar_password BOOL NOT NULL,
    version_sesion INTEGER NOT NULL,
    ultimo_acceso DATETIME,
    creado_en DATETIME NOT NULL,
    CONSTRAINT pk_usuarios PRIMARY KEY (id),
    CONSTRAINT uq_usuarios_username UNIQUE (username),
    CONSTRAINT uq_usuarios_email UNIQUE (email),
    CONSTRAINT fk_usuarios_rol_id FOREIGN KEY(rol_id) REFERENCES roles (id) ON DELETE RESTRICT,
    CONSTRAINT uq_usuarios_empleado_id UNIQUE (empleado_id),
    CONSTRAINT fk_usuarios_empleado_id FOREIGN KEY(empleado_id) REFERENCES empleados (id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Cuentas de acceso. password_hash guarda un hash scrypt, nunca la contraseña';
CREATE INDEX ix_usuarios_rol_id ON usuarios (rol_id);

-- -----------------------------------------------------------------------------
-- cajas: Aperturas/cierres de caja. abierta=1 solo en la caja activa (UNIQUE garantiza una sola)
-- -----------------------------------------------------------------------------
CREATE TABLE cajas (
    id INTEGER NOT NULL AUTO_INCREMENT,
    usuario_apertura_id INTEGER NOT NULL,
    fecha_apertura DATETIME NOT NULL,
    monto_inicial NUMERIC(12, 2) NOT NULL,
    usuario_cierre_id INTEGER,
    fecha_cierre DATETIME,
    monto_esperado NUMERIC(12, 2),
    monto_declarado NUMERIC(12, 2),
    diferencia NUMERIC(12, 2),
    observaciones VARCHAR(255),
    abierta BOOL,
    CONSTRAINT pk_cajas PRIMARY KEY (id),
    CONSTRAINT ck_cajas_monto_inicial_pos CHECK (monto_inicial >= 0),
    CONSTRAINT ck_cajas_abierta_valida CHECK (abierta IS NULL OR abierta = 1),
    CONSTRAINT ck_cajas_estado_coherente CHECK ((abierta = 1 AND fecha_cierre IS NULL) OR (abierta IS NULL AND fecha_cierre IS NOT NULL)),
    CONSTRAINT fk_cajas_usuario_apertura_id FOREIGN KEY(usuario_apertura_id) REFERENCES usuarios (id) ON DELETE RESTRICT,
    CONSTRAINT fk_cajas_usuario_cierre_id FOREIGN KEY(usuario_cierre_id) REFERENCES usuarios (id) ON DELETE RESTRICT,
    CONSTRAINT uq_cajas_abierta UNIQUE (abierta)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Aperturas/cierres de caja. abierta=1 solo en la caja activa (UNIQUE garantiza una sola)';
CREATE INDEX ix_cajas_fecha_apertura ON cajas (fecha_apertura);

-- -----------------------------------------------------------------------------
-- compras: Compras a proveedores
-- -----------------------------------------------------------------------------
CREATE TABLE compras (
    id INTEGER NOT NULL AUTO_INCREMENT,
    proveedor_id INTEGER NOT NULL,
    usuario_id INTEGER NOT NULL,
    fecha DATE NOT NULL,
    numero_comprobante VARCHAR(40),
    total NUMERIC(12, 2) NOT NULL,
    observaciones VARCHAR(255),
    creado_en DATETIME NOT NULL,
    CONSTRAINT pk_compras PRIMARY KEY (id),
    CONSTRAINT uq_compras_proveedor_comprobante UNIQUE (proveedor_id, numero_comprobante),
    CONSTRAINT ck_compras_total_pos CHECK (total >= 0),
    CONSTRAINT fk_compras_proveedor_id FOREIGN KEY(proveedor_id) REFERENCES proveedores (id) ON DELETE RESTRICT,
    CONSTRAINT fk_compras_usuario_id FOREIGN KEY(usuario_id) REFERENCES usuarios (id) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Compras a proveedores';
CREATE INDEX ix_compras_fecha ON compras (fecha);
CREATE INDEX ix_compras_proveedor_id ON compras (proveedor_id);

-- -----------------------------------------------------------------------------
-- gastos: Gastos del negocio
-- -----------------------------------------------------------------------------
CREATE TABLE gastos (
    id INTEGER NOT NULL AUTO_INCREMENT,
    categoria_id INTEGER NOT NULL,
    descripcion VARCHAR(200) NOT NULL,
    monto NUMERIC(12, 2) NOT NULL,
    metodo_pago_id INTEGER NOT NULL,
    fecha DATE NOT NULL,
    usuario_id INTEGER NOT NULL,
    creado_en DATETIME NOT NULL,
    CONSTRAINT pk_gastos PRIMARY KEY (id),
    CONSTRAINT ck_gastos_monto_pos CHECK (monto > 0),
    CONSTRAINT fk_gastos_categoria_id FOREIGN KEY(categoria_id) REFERENCES categorias_gasto (id) ON DELETE RESTRICT,
    CONSTRAINT fk_gastos_metodo_pago_id FOREIGN KEY(metodo_pago_id) REFERENCES metodos_pago (id) ON DELETE RESTRICT,
    CONSTRAINT fk_gastos_usuario_id FOREIGN KEY(usuario_id) REFERENCES usuarios (id) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Gastos del negocio';
CREATE INDEX ix_gastos_categoria_id ON gastos (categoria_id);
CREATE INDEX ix_gastos_fecha ON gastos (fecha);

-- -----------------------------------------------------------------------------
-- password_resets: Tokens de recuperación de contraseña (se guarda el SHA-256 del token)
-- -----------------------------------------------------------------------------
CREATE TABLE password_resets (
    id INTEGER NOT NULL AUTO_INCREMENT,
    usuario_id INTEGER NOT NULL,
    token_hash VARCHAR(64) NOT NULL,
    expira_en DATETIME NOT NULL,
    usado_en DATETIME,
    creado_en DATETIME NOT NULL,
    CONSTRAINT pk_password_resets PRIMARY KEY (id),
    CONSTRAINT fk_password_resets_usuario_id FOREIGN KEY(usuario_id) REFERENCES usuarios (id) ON DELETE CASCADE,
    CONSTRAINT uq_password_resets_token_hash UNIQUE (token_hash)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Tokens de recuperación de contraseña (se guarda el SHA-256 del token)';
CREATE INDEX ix_password_resets_usuario_id ON password_resets (usuario_id);

-- -----------------------------------------------------------------------------
-- detalle_compras: Líneas de compra
-- -----------------------------------------------------------------------------
CREATE TABLE detalle_compras (
    id INTEGER NOT NULL AUTO_INCREMENT,
    compra_id INTEGER NOT NULL,
    producto_id INTEGER NOT NULL,
    cantidad NUMERIC(12, 3) NOT NULL,
    precio_unitario NUMERIC(12, 2) NOT NULL,
    subtotal NUMERIC(12, 2) NOT NULL,
    CONSTRAINT pk_detalle_compras PRIMARY KEY (id),
    CONSTRAINT ck_detalle_compras_cantidad_pos CHECK (cantidad > 0),
    CONSTRAINT ck_detalle_compras_precio_pos CHECK (precio_unitario >= 0),
    CONSTRAINT ck_detalle_compras_subtotal_pos CHECK (subtotal >= 0),
    CONSTRAINT fk_detalle_compras_compra_id FOREIGN KEY(compra_id) REFERENCES compras (id) ON DELETE CASCADE,
    CONSTRAINT fk_detalle_compras_producto_id FOREIGN KEY(producto_id) REFERENCES productos (id) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Líneas de compra';
CREATE INDEX ix_detalle_compras_compra_id ON detalle_compras (compra_id);
CREATE INDEX ix_detalle_compras_producto_id ON detalle_compras (producto_id);

-- -----------------------------------------------------------------------------
-- ventas: Cabecera de ventas (no se borran: cambian de estado)
-- -----------------------------------------------------------------------------
CREATE TABLE ventas (
    id INTEGER NOT NULL AUTO_INCREMENT,
    fecha DATETIME NOT NULL,
    usuario_id INTEGER NOT NULL,
    cliente_id INTEGER,
    caja_id INTEGER,
    subtotal NUMERIC(12, 2) NOT NULL,
    descuento NUMERIC(12, 2) NOT NULL,
    total NUMERIC(12, 2) NOT NULL,
    estado VARCHAR(15) NOT NULL,
    observaciones VARCHAR(255),
    CONSTRAINT pk_ventas PRIMARY KEY (id),
    CONSTRAINT ck_ventas_subtotal_pos CHECK (subtotal >= 0),
    CONSTRAINT ck_ventas_descuento_pos CHECK (descuento >= 0),
    CONSTRAINT ck_ventas_total_pos CHECK (total >= 0),
    CONSTRAINT ck_ventas_estado_valido CHECK (estado IN ('completada','anulada','devuelta')),
    CONSTRAINT fk_ventas_usuario_id FOREIGN KEY(usuario_id) REFERENCES usuarios (id) ON DELETE RESTRICT,
    CONSTRAINT fk_ventas_cliente_id FOREIGN KEY(cliente_id) REFERENCES clientes (id) ON DELETE RESTRICT,
    CONSTRAINT fk_ventas_caja_id FOREIGN KEY(caja_id) REFERENCES cajas (id) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Cabecera de ventas (no se borran: cambian de estado)';
CREATE INDEX ix_ventas_caja_id ON ventas (caja_id);
CREATE INDEX ix_ventas_cliente_id ON ventas (cliente_id);
CREATE INDEX ix_ventas_estado_fecha ON ventas (estado, fecha);
CREATE INDEX ix_ventas_fecha ON ventas (fecha);
CREATE INDEX ix_ventas_usuario_id ON ventas (usuario_id);

-- -----------------------------------------------------------------------------
-- anulaciones_venta: Auditoría de anulaciones y devoluciones
-- -----------------------------------------------------------------------------
CREATE TABLE anulaciones_venta (
    id INTEGER NOT NULL AUTO_INCREMENT,
    venta_id INTEGER NOT NULL,
    tipo VARCHAR(12) NOT NULL,
    motivo VARCHAR(255) NOT NULL,
    reintegra_stock BOOL NOT NULL,
    usuario_id INTEGER NOT NULL,
    caja_id INTEGER,
    fecha DATETIME NOT NULL,
    CONSTRAINT pk_anulaciones_venta PRIMARY KEY (id),
    CONSTRAINT ck_anulaciones_venta_tipo_valido CHECK (tipo IN ('anulacion','devolucion')),
    CONSTRAINT uq_anulaciones_venta_venta_id UNIQUE (venta_id),
    CONSTRAINT fk_anulaciones_venta_venta_id FOREIGN KEY(venta_id) REFERENCES ventas (id) ON DELETE RESTRICT,
    CONSTRAINT fk_anulaciones_venta_usuario_id FOREIGN KEY(usuario_id) REFERENCES usuarios (id) ON DELETE RESTRICT,
    CONSTRAINT fk_anulaciones_venta_caja_id FOREIGN KEY(caja_id) REFERENCES cajas (id) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Auditoría de anulaciones y devoluciones';
CREATE INDEX ix_anulaciones_venta_caja_id ON anulaciones_venta (caja_id);
CREATE INDEX ix_anulaciones_venta_usuario_id ON anulaciones_venta (usuario_id);

-- -----------------------------------------------------------------------------
-- detalle_ventas: Líneas de venta con precio y costo históricos
-- -----------------------------------------------------------------------------
CREATE TABLE detalle_ventas (
    id INTEGER NOT NULL AUTO_INCREMENT,
    venta_id INTEGER NOT NULL,
    producto_id INTEGER NOT NULL,
    cantidad NUMERIC(12, 3) NOT NULL,
    precio_unitario NUMERIC(12, 2) NOT NULL,
    costo_unitario NUMERIC(12, 2) NOT NULL,
    descuento NUMERIC(12, 2) NOT NULL,
    subtotal NUMERIC(12, 2) NOT NULL,
    CONSTRAINT pk_detalle_ventas PRIMARY KEY (id),
    CONSTRAINT ck_detalle_ventas_cantidad_pos CHECK (cantidad > 0),
    CONSTRAINT ck_detalle_ventas_precio_pos CHECK (precio_unitario >= 0),
    CONSTRAINT ck_detalle_ventas_costo_pos CHECK (costo_unitario >= 0),
    CONSTRAINT ck_detalle_ventas_descuento_pos CHECK (descuento >= 0),
    CONSTRAINT ck_detalle_ventas_subtotal_pos CHECK (subtotal >= 0),
    CONSTRAINT fk_detalle_ventas_venta_id FOREIGN KEY(venta_id) REFERENCES ventas (id) ON DELETE CASCADE,
    CONSTRAINT fk_detalle_ventas_producto_id FOREIGN KEY(producto_id) REFERENCES productos (id) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Líneas de venta con precio y costo históricos';
CREATE INDEX ix_detalle_ventas_producto_id ON detalle_ventas (producto_id);
CREATE INDEX ix_detalle_ventas_venta_id ON detalle_ventas (venta_id);

-- -----------------------------------------------------------------------------
-- movimientos_caja: Movimientos de dinero de cada caja
-- -----------------------------------------------------------------------------
CREATE TABLE movimientos_caja (
    id INTEGER NOT NULL AUTO_INCREMENT,
    caja_id INTEGER NOT NULL,
    tipo VARCHAR(12) NOT NULL,
    concepto VARCHAR(150) NOT NULL,
    monto NUMERIC(12, 2) NOT NULL,
    metodo_pago_id INTEGER NOT NULL,
    usuario_id INTEGER NOT NULL,
    venta_id INTEGER,
    gasto_id INTEGER,
    fecha DATETIME NOT NULL,
    CONSTRAINT pk_movimientos_caja PRIMARY KEY (id),
    CONSTRAINT ck_movimientos_caja_tipo_valido CHECK (tipo IN ('venta','ingreso','egreso','retiro','gasto','anulacion')),
    CONSTRAINT ck_movimientos_caja_monto_pos CHECK (monto > 0),
    CONSTRAINT fk_movimientos_caja_caja_id FOREIGN KEY(caja_id) REFERENCES cajas (id) ON DELETE RESTRICT,
    CONSTRAINT fk_movimientos_caja_metodo_pago_id FOREIGN KEY(metodo_pago_id) REFERENCES metodos_pago (id) ON DELETE RESTRICT,
    CONSTRAINT fk_movimientos_caja_usuario_id FOREIGN KEY(usuario_id) REFERENCES usuarios (id) ON DELETE RESTRICT,
    CONSTRAINT fk_movimientos_caja_venta_id FOREIGN KEY(venta_id) REFERENCES ventas (id) ON DELETE RESTRICT,
    CONSTRAINT uq_movimientos_caja_gasto_id UNIQUE (gasto_id),
    CONSTRAINT fk_movimientos_caja_gasto_id FOREIGN KEY(gasto_id) REFERENCES gastos (id) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Movimientos de dinero de cada caja';
CREATE INDEX ix_movimientos_caja_caja_id ON movimientos_caja (caja_id);
CREATE INDEX ix_movimientos_caja_venta_id ON movimientos_caja (venta_id);

-- -----------------------------------------------------------------------------
-- movimientos_stock: Historial de todos los movimientos de inventario
-- -----------------------------------------------------------------------------
CREATE TABLE movimientos_stock (
    id INTEGER NOT NULL AUTO_INCREMENT,
    producto_id INTEGER NOT NULL,
    tipo VARCHAR(12) NOT NULL,
    cantidad NUMERIC(12, 3) NOT NULL,
    stock_anterior NUMERIC(12, 3) NOT NULL,
    stock_nuevo NUMERIC(12, 3) NOT NULL,
    motivo VARCHAR(255) NOT NULL,
    usuario_id INTEGER NOT NULL,
    venta_id INTEGER,
    compra_id INTEGER,
    fecha DATETIME NOT NULL,
    CONSTRAINT pk_movimientos_stock PRIMARY KEY (id),
    CONSTRAINT ck_movimientos_stock_tipo_valido CHECK (tipo IN ('entrada','salida','ajuste','venta','compra','anulacion')),
    CONSTRAINT ck_movimientos_stock_cantidad_no_cero CHECK (cantidad <> 0),
    CONSTRAINT ck_movimientos_stock_stock_nuevo_pos CHECK (stock_nuevo >= 0),
    CONSTRAINT fk_movimientos_stock_producto_id FOREIGN KEY(producto_id) REFERENCES productos (id) ON DELETE RESTRICT,
    CONSTRAINT fk_movimientos_stock_usuario_id FOREIGN KEY(usuario_id) REFERENCES usuarios (id) ON DELETE RESTRICT,
    CONSTRAINT fk_movimientos_stock_venta_id FOREIGN KEY(venta_id) REFERENCES ventas (id) ON DELETE RESTRICT,
    CONSTRAINT fk_movimientos_stock_compra_id FOREIGN KEY(compra_id) REFERENCES compras (id) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Historial de todos los movimientos de inventario';
CREATE INDEX ix_movimientos_stock_compra_id ON movimientos_stock (compra_id);
CREATE INDEX ix_movimientos_stock_fecha ON movimientos_stock (fecha);
CREATE INDEX ix_movimientos_stock_producto_fecha ON movimientos_stock (producto_id, fecha);
CREATE INDEX ix_movimientos_stock_usuario_id ON movimientos_stock (usuario_id);
CREATE INDEX ix_movimientos_stock_venta_id ON movimientos_stock (venta_id);

-- -----------------------------------------------------------------------------
-- pagos: Pagos de cada venta
-- -----------------------------------------------------------------------------
CREATE TABLE pagos (
    id INTEGER NOT NULL AUTO_INCREMENT,
    venta_id INTEGER NOT NULL,
    metodo_pago_id INTEGER NOT NULL,
    monto NUMERIC(12, 2) NOT NULL,
    monto_recibido NUMERIC(12, 2),
    CONSTRAINT pk_pagos PRIMARY KEY (id),
    CONSTRAINT ck_pagos_monto_pos CHECK (monto > 0),
    CONSTRAINT ck_pagos_recibido_valido CHECK (monto_recibido IS NULL OR monto_recibido >= monto),
    CONSTRAINT fk_pagos_venta_id FOREIGN KEY(venta_id) REFERENCES ventas (id) ON DELETE CASCADE,
    CONSTRAINT fk_pagos_metodo_pago_id FOREIGN KEY(metodo_pago_id) REFERENCES metodos_pago (id) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Pagos de cada venta';
CREATE INDEX ix_pagos_metodo_pago_id ON pagos (metodo_pago_id);
CREATE INDEX ix_pagos_venta_id ON pagos (venta_id);

-- =============================================================================
-- Datos base
-- =============================================================================
INSERT INTO permisos (codigo, descripcion) VALUES
  ('dashboard.financiero', 'Ver montos, ganancias y caja en el dashboard'),
  ('ventas.crear', 'Usar el punto de venta'),
  ('ventas.historial', 'Consultar historial de ventas'),
  ('ventas.anular', 'Anular ventas y registrar devoluciones'),
  ('productos.ver', 'Consultar productos y precios'),
  ('productos.gestionar', 'Alta, baja y modificación de productos, categorías y marcas'),
  ('stock.ver', 'Ver stock y alertas'),
  ('stock.ajustar', 'Registrar entradas, salidas y ajustes de stock'),
  ('compras.gestionar', 'Registrar y consultar compras'),
  ('proveedores.gestionar', 'Administrar proveedores'),
  ('clientes.ver', 'Consultar clientes'),
  ('clientes.gestionar', 'Alta y modificación de clientes'),
  ('caja.operar', 'Abrir, registrar movimientos y cerrar caja'),
  ('caja.historial', 'Consultar cierres de caja anteriores'),
  ('gastos.gestionar', 'Registrar y consultar gastos'),
  ('empleados.gestionar', 'Administrar empleados'),
  ('usuarios.gestionar', 'Administrar usuarios y roles'),
  ('reportes.ver', 'Ver reportes');

INSERT INTO roles (nombre, descripcion) VALUES
  ('Dueño', 'Acceso total al sistema'),
  ('Administrador', 'Gestión completa del negocio (no puede modificar al dueño)'),
  ('Vendedor', 'Atiende el mostrador'),
  ('Cajero', 'Atiende el mostrador y maneja la caja');

INSERT INTO rol_permisos (rol_id, permiso_id)
  SELECT r.id, p.id FROM roles r JOIN permisos p ON p.codigo IN ('dashboard.financiero', 'ventas.crear', 'ventas.historial', 'ventas.anular', 'productos.ver', 'productos.gestionar', 'stock.ver', 'stock.ajustar', 'compras.gestionar', 'proveedores.gestionar', 'clientes.ver', 'clientes.gestionar', 'caja.operar', 'caja.historial', 'gastos.gestionar', 'empleados.gestionar', 'usuarios.gestionar', 'reportes.ver')
  WHERE r.nombre = 'Dueño';

INSERT INTO rol_permisos (rol_id, permiso_id)
  SELECT r.id, p.id FROM roles r JOIN permisos p ON p.codigo IN ('dashboard.financiero', 'ventas.crear', 'ventas.historial', 'ventas.anular', 'productos.ver', 'productos.gestionar', 'stock.ver', 'stock.ajustar', 'compras.gestionar', 'proveedores.gestionar', 'clientes.ver', 'clientes.gestionar', 'caja.operar', 'caja.historial', 'gastos.gestionar', 'empleados.gestionar', 'usuarios.gestionar', 'reportes.ver')
  WHERE r.nombre = 'Administrador';

INSERT INTO rol_permisos (rol_id, permiso_id)
  SELECT r.id, p.id FROM roles r JOIN permisos p ON p.codigo IN ('ventas.crear', 'productos.ver', 'stock.ver', 'clientes.ver', 'clientes.gestionar')
  WHERE r.nombre = 'Vendedor';

INSERT INTO rol_permisos (rol_id, permiso_id)
  SELECT r.id, p.id FROM roles r JOIN permisos p ON p.codigo IN ('ventas.crear', 'productos.ver', 'stock.ver', 'clientes.ver', 'clientes.gestionar', 'caja.operar')
  WHERE r.nombre = 'Cajero';

INSERT INTO metodos_pago (codigo, nombre, es_efectivo, orden, activo) VALUES
  ('efectivo', 'Efectivo', 1, 1, 1),
  ('transferencia', 'Transferencia', 0, 2, 1),
  ('debito', 'Débito', 0, 3, 1),
  ('credito', 'Crédito', 0, 4, 1),
  ('mercadopago', 'Mercado Pago', 0, 5, 1),
  ('otro', 'Otro', 0, 6, 1);

INSERT INTO unidades_medida (nombre, abreviatura, permite_decimales) VALUES
  ('Unidad', 'u', 0),
  ('Paquete', 'paq', 0),
  ('Caja', 'cja', 0),
  ('Kilogramo', 'kg', 1),
  ('Litro', 'l', 1),
  ('Gramo', 'g', 1);

INSERT INTO categorias (nombre, activo) VALUES
  ('Bebidas', 1),
  ('Cervezas', 1),
  ('Aguas', 1),
  ('Galletitas', 1),
  ('Alfajores', 1),
  ('Chocolates', 1),
  ('Cigarrillos', 1),
  ('Golosinas', 1),
  ('Snacks', 1),
  ('Limpieza', 1),
  ('Perfumería', 1),
  ('Varios', 1);

INSERT INTO categorias_gasto (nombre, activo) VALUES
  ('Alquiler', 1),
  ('Luz', 1),
  ('Internet', 1),
  ('Proveedores', 1),
  ('Limpieza', 1),
  ('Mantenimiento', 1),
  ('Sueldos', 1),
  ('Impuestos', 1),
  ('Otros', 1);
