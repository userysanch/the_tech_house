-- ============================================================
-- The Tech House - Sistema POS e Inventario
-- Esquema completo: 20 tablas relacionadas (3FN)
-- Motor: Microsoft SQL Server 2022 Express
-- ============================================================

IF DB_ID('TheTechHouse') IS NULL
    CREATE DATABASE TheTechHouse;
GO
USE TheTechHouse;
GO

-- ============================================================
-- CATALOGOS
-- ============================================================

-- 1. roles
CREATE TABLE roles (
    id INT IDENTITY(1,1) PRIMARY KEY,
    nombre VARCHAR(30) UNIQUE NOT NULL,
    descripcion VARCHAR(150) NOT NULL DEFAULT ''
);
GO

-- 2. categorias
CREATE TABLE categorias (
    id INT IDENTITY(1,1) PRIMARY KEY,
    nombre VARCHAR(80) UNIQUE NOT NULL,
    descripcion VARCHAR(200) NOT NULL DEFAULT ''
);
GO

-- 3. marcas
CREATE TABLE marcas (
    id INT IDENTITY(1,1) PRIMARY KEY,
    nombre VARCHAR(80) UNIQUE NOT NULL
);
GO

-- 4. proveedores
CREATE TABLE proveedores (
    id INT IDENTITY(1,1) PRIMARY KEY,
    nombre VARCHAR(150) NOT NULL,
    nit VARCHAR(30) UNIQUE NULL,
    telefono VARCHAR(30) NULL,
    email VARCHAR(100) NULL,
    direccion VARCHAR(200) NULL
);
GO

-- 5. clientes
CREATE TABLE clientes (
    id INT IDENTITY(1,1) PRIMARY KEY,
    nombre VARCHAR(150) NOT NULL,
    nit VARCHAR(30) UNIQUE NULL,
    telefono VARCHAR(30) NULL,
    email VARCHAR(100) NULL,
    direccion VARCHAR(200) NULL
);
GO

-- 6. formas_pago
CREATE TABLE formas_pago (
    id INT IDENTITY(1,1) PRIMARY KEY,
    nombre VARCHAR(50) UNIQUE NOT NULL
);
GO

-- ============================================================
-- USUARIOS E INVENTARIO
-- ============================================================

-- 7. usuarios
CREATE TABLE usuarios (
    id INT IDENTITY(1,1) PRIMARY KEY,
    username VARCHAR(80) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    nombre VARCHAR(150) NOT NULL,
    rol VARCHAR(20) NOT NULL DEFAULT 'empleado',
    rol_id INT NULL,
    CONSTRAINT fk_usuarios_rol FOREIGN KEY (rol_id)
        REFERENCES roles(id) ON DELETE SET NULL
);
GO

-- 8. productos
CREATE TABLE productos (
    id INT IDENTITY(1,1) PRIMARY KEY,
    codigo VARCHAR(50) UNIQUE NOT NULL,
    nombre VARCHAR(150) NOT NULL,
    costo DECIMAL(10, 2) NOT NULL DEFAULT 0.00,
    margen DECIMAL(5, 2) NOT NULL DEFAULT 0.00,
    precio DECIMAL(10, 2) NOT NULL DEFAULT 0.00,
    stock INT NOT NULL DEFAULT 0,
    codigo_barras VARCHAR(50) NULL,
    categoria_id INT NULL,
    marca_id INT NULL,
    proveedor_id INT NULL,
    CONSTRAINT fk_productos_categoria FOREIGN KEY (categoria_id)
        REFERENCES categorias(id) ON DELETE SET NULL,
    CONSTRAINT fk_productos_marca FOREIGN KEY (marca_id)
        REFERENCES marcas(id) ON DELETE SET NULL,
    CONSTRAINT fk_productos_proveedor FOREIGN KEY (proveedor_id)
        REFERENCES proveedores(id) ON DELETE SET NULL
);
GO

-- 9. entradas (compras de mercancia)
CREATE TABLE entradas (
    id INT IDENTITY(1,1) PRIMARY KEY,
    fecha DATETIME2 DEFAULT GETDATE(),
    codigo_producto VARCHAR(50) NOT NULL,
    cantidad INT NOT NULL,
    costo_unitario DECIMAL(10, 2) NOT NULL,
    upc VARCHAR(50) NULL,
    proveedor_id INT NULL,
    CONSTRAINT fk_entradas_producto FOREIGN KEY (codigo_producto)
        REFERENCES productos(codigo),
    CONSTRAINT fk_entradas_proveedor FOREIGN KEY (proveedor_id)
        REFERENCES proveedores(id) ON DELETE SET NULL
);
GO

-- 10. movimientos_inventario (kardex)
CREATE TABLE movimientos_inventario (
    id INT IDENTITY(1,1) PRIMARY KEY,
    codigo_producto VARCHAR(50) NOT NULL,
    tipo VARCHAR(20) NOT NULL,
    cantidad INT NOT NULL,
    fecha DATETIME2 DEFAULT GETDATE(),
    referencia VARCHAR(150) NOT NULL DEFAULT '',
    CONSTRAINT fk_movinv_producto FOREIGN KEY (codigo_producto)
        REFERENCES productos(codigo),
    CONSTRAINT ck_movinv_tipo CHECK (tipo IN ('entrada', 'salida', 'ajuste', 'devolucion'))
);
GO

-- 11. promociones
CREATE TABLE promociones (
    id INT IDENTITY(1,1) PRIMARY KEY,
    codigo_producto VARCHAR(50) NOT NULL,
    descripcion VARCHAR(150) NOT NULL,
    porcentaje DECIMAL(5, 2) NOT NULL DEFAULT 0.00,
    fecha_inicio DATETIME2 NOT NULL,
    fecha_fin DATETIME2 NOT NULL,
    activa BIT NOT NULL DEFAULT 1,
    CONSTRAINT fk_promociones_producto FOREIGN KEY (codigo_producto)
        REFERENCES productos(codigo)
);
GO

-- ============================================================
-- VENTAS Y COBROS
-- ============================================================

-- 12. ventas
CREATE TABLE ventas (
    id INT IDENTITY(1,1) PRIMARY KEY,
    fecha DATETIME2 DEFAULT GETDATE(),
    total_venta DECIMAL(10, 2) NOT NULL DEFAULT 0.00,
    ganancia_total DECIMAL(10, 2) NOT NULL DEFAULT 0.00,
    cliente_id INT NULL,
    CONSTRAINT fk_ventas_cliente FOREIGN KEY (cliente_id)
        REFERENCES clientes(id) ON DELETE SET NULL
);
GO

-- 13. detalle_ventas
CREATE TABLE detalle_ventas (
    id INT IDENTITY(1,1) PRIMARY KEY,
    venta_id INT NOT NULL,
    codigo_producto VARCHAR(50) NOT NULL,
    cantidad INT NOT NULL,
    precio_unitario DECIMAL(10, 2) NOT NULL,
    total DECIMAL(10, 2) NOT NULL,
    ganancia DECIMAL(10, 2) NOT NULL DEFAULT 0,
    CONSTRAINT fk_detalle_venta FOREIGN KEY (venta_id)
        REFERENCES ventas(id) ON DELETE CASCADE,
    CONSTRAINT fk_detalle_producto FOREIGN KEY (codigo_producto)
        REFERENCES productos(codigo)
);
GO

-- 14. pagos_venta (N:N ventas x formas_pago)
CREATE TABLE pagos_venta (
    id INT IDENTITY(1,1) PRIMARY KEY,
    venta_id INT NOT NULL,
    forma_pago_id INT NOT NULL,
    monto DECIMAL(10, 2) NOT NULL,
    fecha DATETIME2 DEFAULT GETDATE(),
    CONSTRAINT fk_pagos_venta FOREIGN KEY (venta_id)
        REFERENCES ventas(id) ON DELETE CASCADE,
    CONSTRAINT fk_pagos_forma FOREIGN KEY (forma_pago_id)
        REFERENCES formas_pago(id)
);
GO

-- 15. devoluciones
CREATE TABLE devoluciones (
    id INT IDENTITY(1,1) PRIMARY KEY,
    venta_id INT NOT NULL,
    fecha DATETIME2 DEFAULT GETDATE(),
    motivo VARCHAR(200) NOT NULL DEFAULT '',
    monto_total DECIMAL(10, 2) NOT NULL DEFAULT 0.00,
    CONSTRAINT fk_devoluciones_venta FOREIGN KEY (venta_id)
        REFERENCES ventas(id)
);
GO

-- 16. detalle_devoluciones
CREATE TABLE detalle_devoluciones (
    id INT IDENTITY(1,1) PRIMARY KEY,
    devolucion_id INT NOT NULL,
    codigo_producto VARCHAR(50) NOT NULL,
    cantidad INT NOT NULL,
    subtotal DECIMAL(10, 2) NOT NULL DEFAULT 0.00,
    CONSTRAINT fk_ddevolucion_dev FOREIGN KEY (devolucion_id)
        REFERENCES devoluciones(id) ON DELETE CASCADE,
    CONSTRAINT fk_ddevolucion_producto FOREIGN KEY (codigo_producto)
        REFERENCES productos(codigo)
);
GO

-- 17. ventas_pendientes (carrito del scanner movil)
CREATE TABLE ventas_pendientes (
    id INT IDENTITY(1,1) PRIMARY KEY,
    scanner_code VARCHAR(50) NOT NULL,
    producto_codigo VARCHAR(50) NOT NULL,
    producto_nombre VARCHAR(150) NOT NULL,
    cantidad INT NOT NULL DEFAULT 1,
    precio_unitario DECIMAL(10, 2) NOT NULL,
    total DECIMAL(10, 2) NOT NULL,
    celular_ip VARCHAR(50) NULL,
    fecha DATETIME2 DEFAULT GETDATE(),
    estado VARCHAR(20) NOT NULL DEFAULT 'pendiente'
);
GO

-- ============================================================
-- CAJA
-- ============================================================

-- 18. cajas
CREATE TABLE cajas (
    id INT IDENTITY(1,1) PRIMARY KEY,
    nombre VARCHAR(60) UNIQUE NOT NULL,
    ubicacion VARCHAR(120) NOT NULL DEFAULT ''
);
GO

-- 19. turnos_caja
CREATE TABLE turnos_caja (
    id INT IDENTITY(1,1) PRIMARY KEY,
    caja_id INT NOT NULL,
    usuario_id INT NOT NULL,
    fecha_apertura DATETIME2 DEFAULT GETDATE(),
    fecha_cierre DATETIME2 NULL,
    saldo_inicial DECIMAL(10, 2) NOT NULL DEFAULT 0.00,
    saldo_final DECIMAL(10, 2) NULL,
    estado VARCHAR(20) NOT NULL DEFAULT 'abierto',
    CONSTRAINT fk_turnos_caja FOREIGN KEY (caja_id)
        REFERENCES cajas(id),
    CONSTRAINT fk_turnos_usuario FOREIGN KEY (usuario_id)
        REFERENCES usuarios(id),
    CONSTRAINT ck_turnos_estado CHECK (estado IN ('abierto', 'cerrado'))
);
GO

-- 20. movimientos_caja
CREATE TABLE movimientos_caja (
    id INT IDENTITY(1,1) PRIMARY KEY,
    turno_id INT NOT NULL,
    tipo VARCHAR(20) NOT NULL,
    monto DECIMAL(10, 2) NOT NULL,
    descripcion VARCHAR(150) NOT NULL DEFAULT '',
    fecha DATETIME2 DEFAULT GETDATE(),
    CONSTRAINT fk_movcaja_turno FOREIGN KEY (turno_id)
        REFERENCES turnos_caja(id),
    CONSTRAINT ck_movcaja_tipo CHECK (tipo IN ('ingreso', 'egreso', 'venta'))
);
GO

-- ============================================================
-- DATOS INICIALES (catalogos y usuarios por defecto)
-- ============================================================

IF NOT EXISTS (SELECT 1 FROM roles WHERE nombre = 'admin')
INSERT INTO roles (nombre, descripcion) VALUES
    ('admin', 'Administrador con acceso total'),
    ('empleado', 'Vendedor o empleado de mostrador');
GO

IF NOT EXISTS (SELECT 1 FROM categorias WHERE nombre = 'General')
INSERT INTO categorias (nombre, descripcion) VALUES
    ('General', 'Sin categoria especifica'),
    ('Electronica', 'Componentes y dispositivos electronicos'),
    ('Accesorios', 'Accesorios y perifericos'),
    ('Software', 'Licencias y productos digitales');
GO

IF NOT EXISTS (SELECT 1 FROM marcas WHERE nombre = 'Generico')
INSERT INTO marcas (nombre) VALUES
    ('Generico'),
    ('Genius'),
    ('Logitech');
GO

IF NOT EXISTS (SELECT 1 FROM formas_pago WHERE nombre = 'Efectivo')
INSERT INTO formas_pago (nombre) VALUES
    ('Efectivo'),
    ('Tarjeta'),
    ('Transferencia');
GO

IF NOT EXISTS (SELECT 1 FROM cajas WHERE nombre = 'Caja 1')
INSERT INTO cajas (nombre, ubicacion) VALUES
    ('Caja 1', 'Mostrador principal');
GO

-- Hashes werkzeug (scrypt) de los usuarios por defecto:
--   admin / admin123     vendedor / vendedor123
IF NOT EXISTS (SELECT 1 FROM usuarios WHERE username = 'admin')
INSERT INTO usuarios (username, password_hash, nombre, rol, rol_id) VALUES
    ('admin', 'scrypt:32768:8:1$O8lfmdi11p5KpeL4$4edc8aa8c617a8ebbac529d563e131ccc495e87b31eaaca0ced7df4628e58a87ef8f2666f9a771e7c360a7ebd3b955b6ed510bc6941630751f141cd966edd7cf', 'Administrador', 'admin', 1),
    ('vendedor', 'scrypt:32768:8:1$tlhqltElWCsWCYx2$1c276cd85e2945401d2e8867065c1575a289075cf785bc53e1445579c7b140f8ca4279a35bed3ce96c640d62365ac20cf55f0306bda9114e345059973efd330b', 'Vendedor', 'empleado', 2);
GO
