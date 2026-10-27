-- ============================================================
-- The Tech House — Elimina los datos de DEMOSTRACION
-- Deja la base solo con los datos sembrados por schema.sql
-- (categorias, marcas, formas de pago, roles, caja y usuarios).
--
-- Uso:
--   sqlcmd -S (local)\SQLEXPRESS -E -d TheTechHouse -i limpiar_demo.sql
-- ============================================================

-- Tablas de transacciones (todo lo que tiene fechas/ventas)
DELETE FROM detalle_devoluciones;
DELETE FROM devoluciones;
DELETE FROM detalle_ventas;
DELETE FROM pagos_venta;
DELETE FROM ventas;
DELETE FROM movimientos_caja;
DELETE FROM turnos_caja;
DELETE FROM movimientos_inventario;
DELETE FROM entradas;
DELETE FROM promociones;
DELETE FROM productos;

-- Catalogos creados por la demo (los de schema.sql permanecen)
DELETE FROM proveedores;
DELETE FROM clientes;

SELECT 'Datos de demostracion eliminados. La base conserva solo los seeds de schema.sql.' AS resultado;
