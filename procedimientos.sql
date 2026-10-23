-- ============================================================
-- The Tech House - Procedimientos almacenados
-- ============================================================

USE the_tech_house;

DELIMITER $$

-- ------------------------------------------------------------
-- sp_registrar_venta
-- Registra una venta completa en UNA sola transaccion:
--   1) Crea la cabecera de la venta.
--   2) Inserta cada item validando stock (SELECT ... FOR UPDATE).
--   3) Descuenta el stock y registra el kardex (salida).
--   4) Guarda el pago en pagos_venta.
--   5) Registra el movimiento de caja si hay turno abierto.
-- Si algo falla: ROLLBACK total y propaga el error.
--   p_items = JSON: [{"codigo":"P001","cantidad":2,"precio":10.50}, ...]
-- ------------------------------------------------------------
DROP PROCEDURE IF EXISTS sp_registrar_venta$$
CREATE PROCEDURE sp_registrar_venta(
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
    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        ROLLBACK;
        RESIGNAL;
    END;

    SET v_n = JSON_LENGTH(p_items);
    IF v_n IS NULL OR v_n = 0 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'La venta no tiene items.';
    END IF;

    START TRANSACTION;

    INSERT INTO ventas (fecha, total_venta, ganancia_total, cliente_id)
    VALUES (NOW(), 0.00, 0.00, p_cliente_id);
    SET p_venta_id = LAST_INSERT_ID();

    WHILE v_i < v_n DO
        SET v_codigo = JSON_UNQUOTE(JSON_EXTRACT(p_items, CONCAT('$[', v_i, '].codigo')));
        SET v_cantidad = CAST(JSON_EXTRACT(p_items, CONCAT('$[', v_i, '].cantidad')) AS UNSIGNED);
        SET v_precio = CAST(JSON_EXTRACT(p_items, CONCAT('$[', v_i, '].precio')) AS DECIMAL(10, 2));

        IF v_cantidad IS NULL OR v_cantidad <= 0 OR v_precio IS NULL OR v_precio < 0 THEN
            SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Item invalido: cantidad o precio fuera de rango.';
        END IF;

        -- Bloqueo pesimista de la fila del producto
        SELECT stock, costo INTO v_stock, v_costo
        FROM productos
        WHERE codigo = v_codigo
        FOR UPDATE;

        IF v_stock IS NULL THEN
            SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Producto no existe.';
        END IF;
        IF v_stock < v_cantidad THEN
            SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Stock insuficiente para uno de los productos.';
        END IF;

        INSERT INTO detalle_ventas (venta_id, codigo_producto, cantidad, precio_unitario, total, ganancia)
        VALUES (p_venta_id, v_codigo, v_cantidad, v_precio,
                v_precio * v_cantidad,
                (v_precio - v_costo) * v_cantidad);

        UPDATE productos SET stock = stock - v_cantidad WHERE codigo = v_codigo;

        INSERT INTO movimientos_inventario (codigo_producto, tipo, cantidad, referencia)
        VALUES (v_codigo, 'salida', v_cantidad, CONCAT('Venta #', p_venta_id));

        SET v_total = v_total + (v_precio * v_cantidad);
        SET v_ganancia = v_ganancia + ((v_precio - v_costo) * v_cantidad);
        SET v_i = v_i + 1;
    END WHILE;

    UPDATE ventas
    SET total_venta = v_total, ganancia_total = v_ganancia
    WHERE id = p_venta_id;

    IF p_forma_pago_id IS NOT NULL THEN
        INSERT INTO pagos_venta (venta_id, forma_pago_id, monto)
        VALUES (p_venta_id, p_forma_pago_id, v_total);
    END IF;

    -- Si hay un turno de caja abierto, deja el ingreso registrado
    SELECT id INTO v_turno_id
    FROM turnos_caja
    WHERE estado = 'abierto'
    ORDER BY fecha_apertura DESC
    LIMIT 1;

    IF v_turno_id IS NOT NULL THEN
        INSERT INTO movimientos_caja (turno_id, tipo, monto, descripcion)
        VALUES (v_turno_id, 'venta', v_total, CONCAT('Venta #', p_venta_id));
    END IF;

    COMMIT;
END$$

-- ------------------------------------------------------------
-- sp_cerrar_caja
-- Cierra un turno de caja: saldo_final = saldo_inicial + ingresos - egresos.
-- ------------------------------------------------------------
DROP PROCEDURE IF EXISTS sp_cerrar_caja$$
CREATE PROCEDURE sp_cerrar_caja(IN p_turno_id INT)
BEGIN
    DECLARE v_estado VARCHAR(20);
    DECLARE v_inicial DECIMAL(10, 2);
    DECLARE v_delta DECIMAL(10, 2);

    SELECT estado, saldo_inicial INTO v_estado, v_inicial
    FROM turnos_caja
    WHERE id = p_turno_id;

    IF v_estado IS NULL THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'El turno de caja no existe.';
    END IF;
    IF v_estado <> 'abierto' THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'El turno de caja ya esta cerrado.';
    END IF;

    SELECT COALESCE(SUM(CASE WHEN tipo IN ('ingreso', 'venta') THEN monto ELSE -monto END), 0)
    INTO v_delta
    FROM movimientos_caja
    WHERE turno_id = p_turno_id;

    UPDATE turnos_caja
    SET saldo_final = v_inicial + v_delta,
        fecha_cierre = NOW(),
        estado = 'cerrado'
    WHERE id = p_turno_id;

    SELECT v_inicial + v_delta AS saldo_final;
END$$

-- ------------------------------------------------------------
-- sp_aplicar_devolucion
-- Devuelve mercancia de una venta: crea la devolucion, repone el
-- stock y registra el kardex. Todo en una transaccion.
--   p_items = JSON: [{"codigo":"P001","cantidad":1}, ...]
-- ------------------------------------------------------------
DROP PROCEDURE IF EXISTS sp_aplicar_devolucion$$
CREATE PROCEDURE sp_aplicar_devolucion(
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
    DECLARE v_existe INT;
    DECLARE v_total DECIMAL(10, 2) DEFAULT 0.00;
    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        ROLLBACK;
        RESIGNAL;
    END;

    SET v_n = JSON_LENGTH(p_items);
    IF v_n IS NULL OR v_n = 0 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'La devolucion no tiene items.';
    END IF;

    START TRANSACTION;

    SELECT COUNT(*) INTO v_existe FROM ventas WHERE id = p_venta_id;
    IF v_existe = 0 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'La venta no existe.';
    END IF;

    INSERT INTO devoluciones (venta_id, motivo, monto_total)
    VALUES (p_venta_id, COALESCE(p_motivo, ''), 0.00);
    SET p_devolucion_id = LAST_INSERT_ID();

    WHILE v_i < v_n DO
        SET v_codigo = JSON_UNQUOTE(JSON_EXTRACT(p_items, CONCAT('$[', v_i, '].codigo')));
        SET v_cantidad = CAST(JSON_EXTRACT(p_items, CONCAT('$[', v_i, '].cantidad')) AS UNSIGNED);

        IF v_cantidad IS NULL OR v_cantidad <= 0 THEN
            SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Item invalido: cantidad fuera de rango.';
        END IF;

        SELECT precio_unitario INTO v_precio
        FROM detalle_ventas
        WHERE venta_id = p_venta_id AND codigo_producto = v_codigo
        ORDER BY id
        LIMIT 1;

        IF v_precio IS NULL THEN
            SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'El producto no pertenece a la venta.';
        END IF;

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
