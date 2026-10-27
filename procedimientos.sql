-- ============================================================
-- The Tech House - Procedimientos almacenados
-- (MySQL equivalente al bloque BEGIN TRY / BEGIN CATCH de SQL Server:
--  todo el cuerpo del procedimiento es el TRY implicito y el
--  manejador de errores que se declara al inicio hace de CATCH.)
-- ============================================================

USE the_tech_house;

DELIMITER $$

-- ------------------------------------------------------------
-- SP_REGISTRARVENTA
-- Registra una venta completa en UNA sola transaccion.
--
-- Orden (igual que el visto en clase):
--   1) Validaciones ANTES de tocar la base.
--   2) BEGIN TRANSACTION (START TRANSACTION en MySQL).
--   3) INSERT venta, INSERT detalle, UPDATE stock.
--   4) COMMIT si todo salio bien.
--   5) Si algo falla, el manejador de errores (CATCH) hace
--      ROLLBACK y propaga el error: no queda nada a medias.
--
-- p_items = JSON: [{"codigo":"P001","cantidad":2,"precio":10.50}, ...]
-- ------------------------------------------------------------
DROP PROCEDURE IF EXISTS SP_REGISTRARVENTA$$
CREATE PROCEDURE SP_REGISTRARVENTA(
    IN p_cliente_id INT,
    IN p_forma_pago_id INT,
    IN p_items JSON,
    OUT p_venta_id INT
)
BEGIN
    DECLARE v_n INT DEFAULT 0;
    DECLARE v_i INT DEFAULT 0;
    DECLARE v_codigo VARCHAR(50);
    DECLARE v_cantidad INT;
    DECLARE v_precio DECIMAL(10, 2);
    DECLARE v_stock INT;
    DECLARE v_costo DECIMAL(10, 2);
    DECLARE v_total DECIMAL(10, 2) DEFAULT 0.00;
    DECLARE v_ganancia DECIMAL(10, 2) DEFAULT 0.00;
    DECLARE v_turno_id INT DEFAULT NULL;

    -- CATCH: si cualquier instruccion falla, se revierte TODO y
    -- se re-lanza el error hacia quien llamo al procedimiento.
    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        ROLLBACK;
        RESIGNAL;
    END;

    -- ============ 1) VALIDACIONES (antes de la transaccion) ============
    SET v_n = JSON_LENGTH(p_items);
    IF v_n IS NULL OR v_n = 0 THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'DEBE ENVIAR AL MENOS UN PRODUCTO';
    END IF;

    -- Recorrer los items para validar cada uno antes de escribir
    WHILE v_i < v_n DO
        SET v_codigo = JSON_UNQUOTE(JSON_EXTRACT(p_items, CONCAT('$[', v_i, '].codigo')));
        SET v_cantidad = CAST(JSON_EXTRACT(p_items, CONCAT('$[', v_i, '].cantidad')) AS UNSIGNED);
        SET v_precio = CAST(JSON_EXTRACT(p_items, CONCAT('$[', v_i, '].precio')) AS DECIMAL(10, 2));

        IF v_cantidad IS NULL OR v_cantidad <= 0 OR v_precio IS NULL OR v_precio < 0 THEN
            SIGNAL SQLSTATE '45000'
                SET MESSAGE_TEXT = 'LA CANTIDAD DEBE SER MAYOR A CERO';
        END IF;

        SELECT stock INTO v_stock
        FROM productos
        WHERE codigo = v_codigo
        FOR UPDATE;   -- bloquea la fila para que nadie venda lo mismo a la vez

        IF v_stock IS NULL THEN
            SIGNAL SQLSTATE '45000'
                SET MESSAGE_TEXT = 'UNO O MAS PRODUCTOS NO EXISTEN';
        END IF;

        IF v_stock < v_cantidad THEN
            SIGNAL SQLSTATE '45000'
                SET MESSAGE_TEXT = 'STOCK INSUFICIENTE PARA UNO O MAS PRODUCTOS';
        END IF;

        SET v_i = v_i + 1;
    END WHILE;

    -- ============ 2) TRANSACCION ============
    START TRANSACTION;

    -- Cabecera de la venta
    INSERT INTO ventas (fecha, total_venta, ganancia_total, cliente_id)
    VALUES (NOW(), 0.00, 0.00, p_cliente_id);
    SET p_venta_id = LAST_INSERT_ID();

    -- Detalle + descuento de stock + kardex
    SET v_i = 0;
    WHILE v_i < v_n DO
        SET v_codigo = JSON_UNQUOTE(JSON_EXTRACT(p_items, CONCAT('$[', v_i, '].codigo')));
        SET v_cantidad = CAST(JSON_EXTRACT(p_items, CONCAT('$[', v_i, '].cantidad')) AS UNSIGNED);
        SET v_precio = CAST(JSON_EXTRACT(p_items, CONCAT('$[', v_i, '].precio')) AS DECIMAL(10, 2));

        SELECT stock, costo INTO v_stock, v_costo
        FROM productos
        WHERE codigo = v_codigo
        FOR UPDATE;

        INSERT INTO detalle_ventas (venta_id, codigo_producto, cantidad, precio_unitario, total, ganancia)
        VALUES (p_venta_id, v_codigo, v_cantidad, v_precio,
                v_precio * v_cantidad,
                (v_precio - v_costo) * v_cantidad);

        UPDATE productos
        SET stock = stock - v_cantidad
        WHERE codigo = v_codigo;

        INSERT INTO movimientos_inventario (codigo_producto, tipo, cantidad, referencia)
        VALUES (v_codigo, 'salida', v_cantidad, CONCAT('Venta #', p_venta_id));

        SET v_total = v_total + (v_precio * v_cantidad);
        SET v_ganancia = v_ganancia + ((v_precio - v_costo) * v_cantidad);
        SET v_i = v_i + 1;
    END WHILE;

    UPDATE ventas
    SET total_venta = v_total, ganancia_total = v_ganancia
    WHERE id = p_venta_id;

    -- Pago
    IF p_forma_pago_id IS NOT NULL THEN
        INSERT INTO pagos_venta (venta_id, forma_pago_id, monto)
        VALUES (p_venta_id, p_forma_pago_id, v_total);
    END IF;

    -- Ingreso de caja si hay turno abierto
    SELECT id INTO v_turno_id
    FROM turnos_caja
    WHERE estado = 'abierto'
    ORDER BY fecha_apertura DESC
    LIMIT 1;

    IF v_turno_id IS NOT NULL THEN
        INSERT INTO movimientos_caja (turno_id, tipo, monto, descripcion)
        VALUES (v_turno_id, 'venta', v_total, CONCAT('Venta #', p_venta_id));
    END IF;

    -- ============ 4) COMMIT ============
    COMMIT;
END$$

-- ------------------------------------------------------------
-- SP_CERRARCAJA
-- Cierra un turno de caja: saldo_final = saldo_inicial + ingresos - egresos.
-- Valida primero; luego UPDATE en una sola transaccion.
-- ------------------------------------------------------------
DROP PROCEDURE IF EXISTS SP_CERRARCAJA$$
CREATE PROCEDURE SP_CERRARCAJA(IN p_turno_id INT)
BEGIN
    DECLARE v_estado VARCHAR(20);
    DECLARE v_inicial DECIMAL(10, 2);
    DECLARE v_delta DECIMAL(10, 2);

    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        ROLLBACK;
        RESIGNAL;
    END;

    -- 1) VALIDACIONES
    SELECT estado, saldo_inicial INTO v_estado, v_inicial
    FROM turnos_caja
    WHERE id = p_turno_id
    FOR UPDATE;

    IF v_estado IS NULL THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'EL TURNO DE CAJA NO EXISTE';
    END IF;

    IF v_estado <> 'abierto' THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'EL TURNO DE CAJA YA ESTA CERRADO';
    END IF;

    -- 2) TRANSACCION
    START TRANSACTION;

    SELECT COALESCE(SUM(CASE WHEN tipo IN ('ingreso', 'venta') THEN monto ELSE -monto END), 0)
    INTO v_delta
    FROM movimientos_caja
    WHERE turno_id = p_turno_id;

    UPDATE turnos_caja
    SET saldo_final = v_inicial + v_delta,
        fecha_cierre = NOW(),
        estado = 'cerrado'
    WHERE id = p_turno_id;

    COMMIT;

    SELECT v_inicial + v_delta AS saldo_final;
END$$

-- ------------------------------------------------------------
-- SP_APLICARDEVOLUCION
-- Devuelve mercancia de una venta: crea la devolucion, repone el
-- stock y registra el kardex. Todo en una transaccion.
--   p_items = JSON: [{"codigo":"P001","cantidad":1}, ...]
-- ------------------------------------------------------------
DROP PROCEDURE IF EXISTS SP_APLICARDEVOLUCION$$
CREATE PROCEDURE SP_APLICARDEVOLUCION(
    IN p_venta_id INT,
    IN p_motivo VARCHAR(200),
    IN p_items JSON,
    OUT p_devolucion_id INT
)
BEGIN
    DECLARE v_n INT DEFAULT 0;
    DECLARE v_i INT DEFAULT 0;
    DECLARE v_codigo VARCHAR(50);
    DECLARE v_cantidad INT;
    DECLARE v_precio DECIMAL(10, 2);
    DECLARE v_vendido INT;
    DECLARE v_devuelto INT;
    DECLARE v_existe INT;
    DECLARE v_total DECIMAL(10, 2) DEFAULT 0.00;

    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        ROLLBACK;
        RESIGNAL;
    END;

    -- ============ 1) VALIDACIONES ============
    SET v_n = JSON_LENGTH(p_items);
    IF v_n IS NULL OR v_n = 0 THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'LA DEVOLUCION NO TIENE ITEMS';
    END IF;

    SELECT COUNT(*) INTO v_existe FROM ventas WHERE id = p_venta_id;
    IF v_existe = 0 THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'LA VENTA NO EXISTE';
    END IF;

    WHILE v_i < v_n DO
        SET v_codigo = JSON_UNQUOTE(JSON_EXTRACT(p_items, CONCAT('$[', v_i, '].codigo')));
        SET v_cantidad = CAST(JSON_EXTRACT(p_items, CONCAT('$[', v_i, '].cantidad')) AS UNSIGNED);

        IF v_cantidad IS NULL OR v_cantidad <= 0 THEN
            SIGNAL SQLSTATE '45000'
                SET MESSAGE_TEXT = 'LA CANTIDAD DEBE SER MAYOR A CERO';
        END IF;

        -- Cuanto se vendio y cuanto ya se devolvio de ese producto en esa venta
        SELECT COALESCE(SUM(cantidad), 0) INTO v_vendido
        FROM detalle_ventas
        WHERE venta_id = p_venta_id AND codigo_producto = v_codigo;

        IF v_vendido = 0 THEN
            SIGNAL SQLSTATE '45000'
                SET MESSAGE_TEXT = 'EL PRODUCTO NO PERTENECE A ESA VENTA';
        END IF;

        SELECT COALESCE(SUM(d.cantidad), 0) INTO v_devuelto
        FROM detalle_devoluciones d
        JOIN devoluciones dv ON dv.id = d.devolucion_id
        WHERE dv.venta_id = p_venta_id AND d.codigo_producto = v_codigo;

        IF v_devuelto + v_cantidad > v_vendido THEN
            SIGNAL SQLSTATE '45000'
                SET MESSAGE_TEXT = 'NO SE PUEDE DEVOLVER MAS DE LO VENDIDO';
        END IF;

        SET v_i = v_i + 1;
    END WHILE;

    -- ============ 2) TRANSACCION ============
    START TRANSACTION;

    INSERT INTO devoluciones (venta_id, motivo, monto_total)
    VALUES (p_venta_id, COALESCE(p_motivo, ''), 0.00);
    SET p_devolucion_id = LAST_INSERT_ID();

    SET v_i = 0;
    WHILE v_i < v_n DO
        SET v_codigo = JSON_UNQUOTE(JSON_EXTRACT(p_items, CONCAT('$[', v_i, '].codigo')));
        SET v_cantidad = CAST(JSON_EXTRACT(p_items, CONCAT('$[', v_i, '].cantidad')) AS UNSIGNED);

        SELECT precio_unitario INTO v_precio
        FROM detalle_ventas
        WHERE venta_id = p_venta_id AND codigo_producto = v_codigo
        ORDER BY id
        LIMIT 1;

        INSERT INTO detalle_devoluciones (devolucion_id, codigo_producto, cantidad, subtotal)
        VALUES (p_devolucion_id, v_codigo, v_cantidad, v_precio * v_cantidad);

        UPDATE productos SET stock = stock + v_cantidad WHERE codigo = v_codigo;

        INSERT INTO movimientos_inventario (codigo_producto, tipo, cantidad, referencia)
        VALUES (v_codigo, 'devolucion', v_cantidad, CONCAT('Devolucion #', p_devolucion_id));

        SET v_total = v_total + (v_precio * v_cantidad);
        SET v_i = v_i + 1;
    END WHILE;

    UPDATE devoluciones SET monto_total = v_total WHERE id = p_devolucion_id;

    COMMIT;

    SELECT v_total AS monto_total;
END$$

DELIMITER ;
