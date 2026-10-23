-- ============================================================
-- The Tech House - Sistema POS e Inventario
-- Esquema completo: 20 tablas relacionadas (3FN)
-- ============================================================

CREATE DATABASE IF NOT EXISTS the_tech_house CHARACTER SET utf8mb4 COLLATE utf8mb4_spanish_ci;
USE the_tech_house;

-- ============================================================
-- CATALOGOS (entidades debiles de referencia)
-- ============================================================

-- 1. roles
CREATE TABLE IF NOT EXISTS roles (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(30) UNIQUE NOT NULL,
    descripcion VARCHAR(150) NOT NULL DEFAULT ''
);

-- 2. categorias
CREATE TABLE IF NOT EXISTS categorias (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(80) UNIQUE NOT NULL,
    descripcion VARCHAR(200) NOT NULL DEFAULT ''
);

-- 3. marcas
CREATE TABLE IF NOT EXISTS marcas (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(80) UNIQUE NOT NULL
);

-- 4. proveedores
CREATE TABLE IF NOT EXISTS proveedores (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(150) NOT NULL,
    nit VARCHAR(30) UNIQUE,
    telefono VARCHAR(30) DEFAULT NULL,
    email VARCHAR(100) DEFAULT NULL,
    direccion VARCHAR(200) DEFAULT NULL
);

-- 5. clientes
CREATE TABLE IF NOT EXISTS clientes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(150) NOT NULL,
    nit VARCHAR(30) UNIQUE,
    telefono VARCHAR(30) DEFAULT NULL,
    email VARCHAR(100) DEFAULT NULL,
    direccion VARCHAR(200) DEFAULT NULL
);

-- 6. formas_pago
CREATE TABLE IF NOT EXISTS formas_pago (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(50) UNIQUE NOT NULL
);

-- ============================================================
-- USUARIOS E INVENTARIO
-- ============================================================

-- 7. usuarios
CREATE TABLE IF NOT EXISTS usuarios (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(80) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    nombre VARCHAR(150) NOT NULL,
    rol VARCHAR(20) NOT NULL DEFAULT 'empleado',
    rol_id INT DEFAULT NULL,
    CONSTRAINT fk_usuarios_rol FOREIGN KEY (rol_id)
        REFERENCES roles(id) ON DELETE SET NULL ON UPDATE CASCADE
);

-- 8. categorias / marcas / proveedores ligados a productos
-- 8. productos
CREATE TABLE IF NOT EXISTS productos (
    id INT AUTO_INCREMENT PRIMARY KEY,
    codigo VARCHAR(50) UNIQUE NOT NULL,
    nombre VARCHAR(150) NOT NULL,
    costo DECIMAL(10, 2) NOT NULL DEFAULT 0.00,
    margen DECIMAL(5, 2) NOT NULL DEFAULT 0.00,
    precio DECIMAL(10, 2) NOT NULL DEFAULT 0.00,
    stock INT NOT NULL DEFAULT 0,
    codigo_barras VARCHAR(50) DEFAULT NULL,
    categoria_id INT DEFAULT NULL,
    marca_id INT DEFAULT NULL,
    proveedor_id INT DEFAULT NULL,
    CONSTRAINT fk_productos_categoria FOREIGN KEY (categoria_id)
        REFERENCES categorias(id) ON DELETE SET NULL ON UPDATE CASCADE,
    CONSTRAINT fk_productos_marca FOREIGN KEY (marca_id)
        REFERENCES marcas(id) ON DELETE SET NULL ON UPDATE CASCADE,
    CONSTRAINT fk_productos_proveedor FOREIGN KEY (proveedor_id)
        REFERENCES proveedores(id) ON DELETE SET NULL ON UPDATE CASCADE
);

-- 9. entradas (compras de mercancia)
CREATE TABLE IF NOT EXISTS entradas (
    id INT AUTO_INCREMENT PRIMARY KEY,
    fecha DATETIME DEFAULT CURRENT_TIMESTAMP,
    codigo_producto VARCHAR(50) NOT NULL,
    cantidad INT NOT NULL,
    costo_unitario DECIMAL(10, 2) NOT NULL,
    upc VARCHAR(50) DEFAULT NULL,
    proveedor_id INT DEFAULT NULL,
    CONSTRAINT fk_entradas_producto FOREIGN KEY (codigo_producto)
        REFERENCES productos(codigo) ON UPDATE CASCADE,
    CONSTRAINT fk_entradas_proveedor FOREIGN KEY (proveedor_id)
        REFERENCES proveedores(id) ON DELETE SET NULL ON UPDATE CASCADE
);

-- 10. movimientos_inventario (kardex)
CREATE TABLE IF NOT EXISTS movimientos_inventario (
    id INT AUTO_INCREMENT PRIMARY KEY,
    codigo_producto VARCHAR(50) NOT NULL,
    tipo ENUM('entrada', 'salida', 'ajuste', 'devolucion') NOT NULL,
    cantidad INT NOT NULL,
    fecha DATETIME DEFAULT CURRENT_TIMESTAMP,
    referencia VARCHAR(150) NOT NULL DEFAULT '',
    CONSTRAINT fk_movinv_producto FOREIGN KEY (codigo_producto)
        REFERENCES productos(codigo) ON UPDATE CASCADE
);

-- 11. promociones
CREATE TABLE IF NOT EXISTS promociones (
    id INT AUTO_INCREMENT PRIMARY KEY,
    codigo_producto VARCHAR(50) NOT NULL,
    descripcion VARCHAR(150) NOT NULL,
    porcentaje DECIMAL(5, 2) NOT NULL DEFAULT 0.00,
    fecha_inicio DATETIME NOT NULL,
    fecha_fin DATETIME NOT NULL,
    activa TINYINT(1) NOT NULL DEFAULT 1,
    CONSTRAINT fk_promociones_producto FOREIGN KEY (codigo_producto)
        REFERENCES productos(codigo) ON UPDATE CASCADE
);

-- ============================================================
-- VENTAS Y COBROS
-- ============================================================

-- 12. ventas
CREATE TABLE IF NOT EXISTS ventas (
    id INT AUTO_INCREMENT PRIMARY KEY,
    fecha DATETIME DEFAULT CURRENT_TIMESTAMP,
    total_venta DECIMAL(10, 2) NOT NULL DEFAULT 0.00,
    ganancia_total DECIMAL(10, 2) NOT NULL DEFAULT 0.00,
    cliente_id INT DEFAULT NULL,
    CONSTRAINT fk_ventas_cliente FOREIGN KEY (cliente_id)
        REFERENCES clientes(id) ON DELETE SET NULL ON UPDATE CASCADE
);

-- 13. detalle_ventas
CREATE TABLE IF NOT EXISTS detalle_ventas (
    id INT AUTO_INCREMENT PRIMARY KEY,
    venta_id INT NOT NULL,
    codigo_producto VARCHAR(50) NOT NULL,
    cantidad INT NOT NULL,
    precio_unitario DECIMAL(10, 2) NOT NULL,
    total DECIMAL(10, 2) NOT NULL,
    ganancia DECIMAL(10, 2) NOT NULL DEFAULT 0,
    CONSTRAINT fk_detalle_venta FOREIGN KEY (venta_id)
        REFERENCES ventas(id) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_detalle_producto FOREIGN KEY (codigo_producto)
        REFERENCES productos(codigo) ON UPDATE CASCADE
);

-- 14. pagos_venta (N:N ventas x formas_pago)
CREATE TABLE IF NOT EXISTS pagos_venta (
    id INT AUTO_INCREMENT PRIMARY KEY,
    venta_id INT NOT NULL,
    forma_pago_id INT NOT NULL,
    monto DECIMAL(10, 2) NOT NULL,
    fecha DATETIME DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_pagos_venta FOREIGN KEY (venta_id)
        REFERENCES ventas(id) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_pagos_forma FOREIGN KEY (forma_pago_id)
        REFERENCES formas_pago(id) ON UPDATE CASCADE
);

-- 15. devoluciones
CREATE TABLE IF NOT EXISTS devoluciones (
    id INT AUTO_INCREMENT PRIMARY KEY,
    venta_id INT NOT NULL,
    fecha DATETIME DEFAULT CURRENT_TIMESTAMP,
    motivo VARCHAR(200) NOT NULL DEFAULT '',
    monto_total DECIMAL(10, 2) NOT NULL DEFAULT 0.00,
    CONSTRAINT fk_devoluciones_venta FOREIGN KEY (venta_id)
        REFERENCES ventas(id) ON UPDATE CASCADE
);

-- 16. detalle_devoluciones
CREATE TABLE IF NOT EXISTS detalle_devoluciones (
    id INT AUTO_INCREMENT PRIMARY KEY,
    devolucion_id INT NOT NULL,
    codigo_producto VARCHAR(50) NOT NULL,
    cantidad INT NOT NULL,
    subtotal DECIMAL(10, 2) NOT NULL DEFAULT 0.00,
    CONSTRAINT fk_ddevolucion_dev FOREIGN KEY (devolucion_id)
        REFERENCES devoluciones(id) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_ddevolucion_producto FOREIGN KEY (codigo_producto)
        REFERENCES productos(codigo) ON UPDATE CASCADE
);

-- 17. ventas_pendientes (carrito del scanner movil)
CREATE TABLE IF NOT EXISTS ventas_pendientes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    scanner_code VARCHAR(50) NOT NULL,
    producto_codigo VARCHAR(50) NOT NULL,
    producto_nombre VARCHAR(150) NOT NULL,
    cantidad INT NOT NULL DEFAULT 1,
    precio_unitario DECIMAL(10, 2) NOT NULL,
    total DECIMAL(10, 2) NOT NULL,
    celular_ip VARCHAR(50) DEFAULT NULL,
    fecha DATETIME DEFAULT CURRENT_TIMESTAMP,
    estado VARCHAR(20) NOT NULL DEFAULT 'pendiente'
);

-- ============================================================
-- CAJA
-- ============================================================

-- 18. cajas
CREATE TABLE IF NOT EXISTS cajas (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(60) UNIQUE NOT NULL,
    ubicacion VARCHAR(120) NOT NULL DEFAULT ''
);

-- 19. turnos_caja
CREATE TABLE IF NOT EXISTS turnos_caja (
    id INT AUTO_INCREMENT PRIMARY KEY,
    caja_id INT NOT NULL,
    usuario_id INT NOT NULL,
    fecha_apertura DATETIME DEFAULT CURRENT_TIMESTAMP,
    fecha_cierre DATETIME DEFAULT NULL,
    saldo_inicial DECIMAL(10, 2) NOT NULL DEFAULT 0.00,
    saldo_final DECIMAL(10, 2) DEFAULT NULL,
    estado ENUM('abierto', 'cerrado') NOT NULL DEFAULT 'abierto',
    CONSTRAINT fk_turnos_caja FOREIGN KEY (caja_id)
        REFERENCES cajas(id) ON UPDATE CASCADE,
    CONSTRAINT fk_turnos_usuario FOREIGN KEY (usuario_id)
        REFERENCES usuarios(id) ON UPDATE CASCADE
);

-- 20. movimientos_caja
CREATE TABLE IF NOT EXISTS movimientos_caja (
    id INT AUTO_INCREMENT PRIMARY KEY,
    turno_id INT NOT NULL,
    tipo ENUM('ingreso', 'egreso', 'venta') NOT NULL,
    monto DECIMAL(10, 2) NOT NULL,
    descripcion VARCHAR(150) NOT NULL DEFAULT '',
    fecha DATETIME DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_movcaja_turno FOREIGN KEY (turno_id)
        REFERENCES turnos_caja(id) ON UPDATE CASCADE
);

-- ============================================================
-- DATOS INICIALES (catalogos y usuarios por defecto)
-- ============================================================

INSERT IGNORE INTO roles (nombre, descripcion) VALUES
    ('admin', 'Administrador con acceso total'),
    ('empleado', 'Vendedor o empleado de mostrador');

INSERT IGNORE INTO categorias (nombre, descripcion) VALUES
    ('General', 'Sin categoria especifica'),
    ('Electronica', 'Componentes y dispositivos electronicos'),
    ('Accesorios', 'Accesorios y perifericos'),
    ('Software', 'Licencias y productos digitales');

INSERT IGNORE INTO marcas (nombre) VALUES
    ('Generico'),
    ('Genius'),
    ('Logitech');

INSERT IGNORE INTO formas_pago (nombre) VALUES
    ('Efectivo'),
    ('Tarjeta'),
    ('Transferencia');

INSERT IGNORE INTO cajas (nombre, ubicacion) VALUES
    ('Caja 1', 'Mostrador principal');

-- Hashes werkzeug (scrypt) de los usuarios por defecto:
--   admin / admin123     vendedor / vendedor123
INSERT IGNORE INTO usuarios (username, password_hash, nombre, rol, rol_id) VALUES
    ('admin', 'scrypt:32768:8:1$O8lfmdi11p5KpeL4$4edc8aa8c617a8ebbac529d563e131ccc495e87b31eaaca0ced7df4628e58a87ef8f2666f9a771e7c360a7ebd3b955b6ed510bc6941630751f141cd966edd7cf', 'Administrador', 'admin', 1),
    ('vendedor', 'scrypt:32768:8:1$tlhqltElWCsWCYx2$1c276cd85e2945401d2e8867065c1575a289075cf785bc53e1445579c7b140f8ca4279a35bed3ce96c640d62365ac20cf55f0306bda9114e345059973efd330b', 'Vendedor', 'empleado', 2);
