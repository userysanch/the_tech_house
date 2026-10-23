-- ============================================================
-- The Tech House — Elimina los datos de DEMOSTRACION
-- Deja la base solo con los datos sembrados por schema.sql
-- (categorias, marcas, formas de pago, roles, caja y usuarios).
--
-- Uso:  mysql -u root -p the_tech_house < limpiar_demo.sql
-- ============================================================

SET FOREIGN_KEY_CHECKS = 0;

-- Tablas de transacciones (todo lo que tiene fechas/ventas)
TRUNCATE TABLE detalle_devoluciones;
TRUNCATE TABLE devoluciones;
TRUNCATE TABLE detalle_ventas;
TRUNCATE TABLE pagos_venta;
TRUNCATE TABLE ventas;
TRUNCATE TABLE movimientos_caja;
TRUNCATE TABLE turnos_caja;
TRUNCATE TABLE movimientos_inventario;
TRUNCATE TABLE entradas;
TRUNCATE TABLE promociones;
TRUNCATE TABLE productos;

-- Catalogos creados por la demo (los de schema.sql permanecen)
DELETE FROM proveedores;
DELETE FROM clientes;

SET FOREIGN_KEY_CHECKS = 1;

SELECT 'Datos de demostracion eliminados. La base conserva solo los seeds de schema.sql.' AS resultado;
