-- ============================================================
-- The Tech House - Procedimientos almacenados
-- Motor: Microsoft SQL Server (T-SQL)
-- Estructura: BEGIN TRY / BEGIN CATCH con transacciones,
-- igual que el patron visto en clase.
-- ============================================================

USE TheTechHouse;
GO

-- Tipo de tabla para enviar el detalle de la venta / devolucion
-- (equivalente a la tabla tipo TIPODETALLEVENTA de la clase)
IF TYPE_ID('dbo.TIPODETALLEVENTA') IS NOT NULL
    DROP TYPE dbo.TIPODETALLEVENTA;
GO
CREATE TYPE dbo.TIPODETALLEVENTA AS TABLE (
    CODIGOPRODUCTO VARCHAR(50),
    CANTIDAD INT,
    PRECIO DECIMAL(10, 2)
);
GO

-- ------------------------------------------------------------
-- SP_REGISTRARVENTA
-- Registra una venta completa en UNA sola transaccion:
--   1) Cabecera de la venta.
--   2) Detalle de cada item.
--   3) Descuento de existencias.
--   4) Kardex (salida), pago y movimiento de caja.
-- Si algo falla: ROLLBACK total y propaga el error (THROW).
-- ------------------------------------------------------------
IF OBJECT_ID('dbo.SP_REGISTRARVENTA', 'P') IS NOT NULL
    DROP PROCEDURE dbo.SP_REGISTRARVENTA;
GO
CREATE PROCEDURE SP_REGISTRARVENTA
    @CLIENTE_ID INT,
    @FORMA_PAGOID INT,
    @DETALLES TIPODETALLEVENTA READONLY,
    @VENTA_ID INT OUTPUT
AS
BEGIN
    SET NOCOUNT ON;

    BEGIN TRY
        BEGIN TRANSACTION;

        -- ============ VALIDACIONES ============
        IF NOT EXISTS (SELECT 1 FROM @DETALLES)
        BEGIN;
            THROW 50001, 'DEBE ENVIAR AL MENOS UN PRODUCTO', 1;
        END;

        IF EXISTS (SELECT 1 FROM @DETALLES WHERE CANTIDAD <= 0)
        BEGIN;
            THROW 50002, 'LA CANTIDAD DEBE SER MAYOR A CERO', 1;
        END;

        IF EXISTS (
            SELECT 1 FROM @DETALLES D
            WHERE D.CODIGOPRODUCTO NOT IN (SELECT CODIGO FROM PRODUCTOS)
        )
        BEGIN;
            THROW 50003, 'UNO O MAS PRODUCTOS NO EXISTEN', 1;
        END;

        IF EXISTS (
            SELECT 1 FROM @DETALLES D
            WHERE D.CANTIDAD > (SELECT STOCK FROM PRODUCTOS WHERE CODIGO = D.CODIGOPRODUCTO)
        )
        BEGIN;
            THROW 50004, 'STOCK INSUFICIENTE PARA UNO O MAS PRODUCTOS', 1;
        END;

        -- ============ TOTAL ============
        DECLARE @TOTAL DECIMAL(10,2);
        DECLARE @GANANCIA DECIMAL(10,2);
        SELECT @TOTAL = SUM(D.CANTIDAD * D.PRECIO),
               @GANANCIA = SUM(D.CANTIDAD * (D.PRECIO - P.COSTO))
        FROM @DETALLES D
        INNER JOIN PRODUCTOS P ON P.CODIGO = D.CODIGOPRODUCTO;

        -- ============ CABECERA DE LA VENTA ============
        INSERT INTO VENTAS (FECHA, TOTAL_VENTA, GANANCIA_TOTAL, CLIENTE_ID)
        VALUES (GETDATE(), @TOTAL, @GANANCIA, @CLIENTE_ID);

        SET @VENTA_ID = SCOPE_IDENTITY();

        -- ============ DETALLE + EXISTENCIAS + KARDEX ============
        INSERT INTO DETALLE_VENTAS (VENTA_ID, CODIGO_PRODUCTO, CANTIDAD, PRECIO_UNITARIO, TOTAL, GANANCIA)
        SELECT @VENTA_ID, D.CODIGOPRODUCTO, D.CANTIDAD, D.PRECIO,
               D.CANTIDAD * D.PRECIO,
               D.CANTIDAD * (D.PRECIO - P.COSTO)
        FROM @DETALLES D
        INNER JOIN PRODUCTOS P ON P.CODIGO = D.CODIGOPRODUCTO;

        UPDATE PRODUCTOS
        SET STOCK = STOCK - D.CANTIDAD
        FROM PRODUCTOS P
        INNER JOIN @DETALLES D ON D.CODIGOPRODUCTO = P.CODIGO;

        INSERT INTO MOVIMIENTOS_INVENTARIO (CODIGO_PRODUCTO, TIPO, CANTIDAD, REFERENCIA)
        SELECT CODIGOPRODUCTO, 'salida', CANTIDAD, CONCAT('Venta #', @VENTA_ID)
        FROM @DETALLES;

        -- ============ PAGO ============
        IF @FORMA_PAGOID IS NOT NULL
        BEGIN
            INSERT INTO PAGOS_VENTA (VENTA_ID, FORMA_PAGO_ID, MONTO)
            VALUES (@VENTA_ID, @FORMA_PAGOID, @TOTAL);
        END;

        -- ============ MOVIMIENTO DE CAJA (si hay turno abierto) ============
        DECLARE @TURNO_ID INT;
        SELECT TOP 1 @TURNO_ID = ID
        FROM TURNOS_CAJA
        WHERE ESTADO = 'abierto'
        ORDER BY FECHA_APERTURA DESC;

        IF @TURNO_ID IS NOT NULL
        BEGIN
            INSERT INTO MOVIMIENTOS_CAJA (TURNO_ID, TIPO, MONTO, DESCRIPCION)
            VALUES (@TURNO_ID, 'venta', @TOTAL, CONCAT('Venta #', @VENTA_ID));
        END;

        COMMIT TRANSACTION;
        PRINT 'VENTA REGISTRADA CORRECTAMENTE. TOTAL: ' + CAST(@TOTAL AS VARCHAR);

    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        PRINT 'ERROR: ' + ERROR_MESSAGE();
        THROW;
    END CATCH
END
GO

-- ------------------------------------------------------------
-- SP_CERRARCAJA
-- Cierra un turno de caja: saldo_final = saldo_inicial + ingresos - egresos.
-- ------------------------------------------------------------
IF OBJECT_ID('dbo.SP_CERRARCAJA', 'P') IS NOT NULL
    DROP PROCEDURE dbo.SP_CERRARCAJA;
GO
CREATE PROCEDURE SP_CERRARCAJA
    @TURNO_ID INT
AS
BEGIN
    SET NOCOUNT ON;

    BEGIN TRY
        BEGIN TRANSACTION;

        -- ============ VALIDACIONES ============
        DECLARE @ESTADO VARCHAR(20);
        DECLARE @INICIAL DECIMAL(10,2);

        SELECT @ESTADO = ESTADO, @INICIAL = SALDO_INICIAL
        FROM TURNOS_CAJA
        WHERE ID = @TURNO_ID;

        IF @ESTADO IS NULL
        BEGIN;
            THROW 50006, 'EL TURNO DE CAJA NO EXISTE', 1;
        END;

        IF @ESTADO <> 'abierto'
        BEGIN;
            THROW 50007, 'EL TURNO DE CAJA YA ESTA CERRADO', 1;
        END;

        -- ============ CALCULO Y CIERRE ============
        DECLARE @DELTA DECIMAL(10,2);
        SELECT @DELTA = COALESCE(SUM(CASE WHEN TIPO IN ('ingreso', 'venta') THEN MONTO ELSE -MONTO END), 0)
        FROM MOVIMIENTOS_CAJA
        WHERE TURNO_ID = @TURNO_ID;

        UPDATE TURNOS_CAJA
        SET SALDO_FINAL = @INICIAL + @DELTA,
            FECHA_CIERRE = GETDATE(),
            ESTADO = 'cerrado'
        WHERE ID = @TURNO_ID;

        COMMIT TRANSACTION;
        PRINT 'CAJA CERRADA. SALDO FINAL: ' + CAST(@INICIAL + @DELTA AS VARCHAR);

    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        PRINT 'ERROR: ' + ERROR_MESSAGE();
        THROW;
    END CATCH
END
GO

-- ------------------------------------------------------------
-- SP_APLICARDEVOLUCION
-- Devuelve mercancia de una venta: crea la devolucion, repone el
-- stock y registra el kardex. Todo en una transaccion.
-- ------------------------------------------------------------
IF OBJECT_ID('dbo.SP_APLICARDEVOLUCION', 'P') IS NOT NULL
    DROP PROCEDURE dbo.SP_APLICARDEVOLUCION;
GO
CREATE PROCEDURE SP_APLICARDEVOLUCION
    @VENTA_ID INT,
    @MOTIVO VARCHAR(200),
    @DETALLES TIPODETALLEVENTA READONLY,
    @DEVOLUCION_ID INT OUTPUT
AS
BEGIN
    SET NOCOUNT ON;

    BEGIN TRY
        BEGIN TRANSACTION;

        -- ============ VALIDACIONES ============
        IF NOT EXISTS (SELECT 1 FROM @DETALLES)
        BEGIN;
            THROW 50011, 'LA DEVOLUCION NO TIENE ITEMS', 1;
        END;

        IF NOT EXISTS (SELECT 1 FROM VENTAS WHERE ID = @VENTA_ID)
        BEGIN;
            THROW 50012, 'LA VENTA NO EXISTE', 1;
        END;

        IF EXISTS (SELECT 1 FROM @DETALLES WHERE CANTIDAD <= 0)
        BEGIN;
            THROW 50002, 'LA CANTIDAD DEBE SER MAYOR A CERO', 1;
        END;

        -- El producto debe pertenecer a la venta y no se puede devolver
        -- mas de lo que se vendio (vendido - ya devuelto).
        IF EXISTS (
            SELECT 1 FROM @DETALLES D
            WHERE NOT EXISTS (
                SELECT 1 FROM DETALLE_VENTAS DV
                WHERE DV.VENTA_ID = @VENTA_ID
                  AND DV.CODIGO_PRODUCTO = D.CODIGOPRODUCTO
            )
        )
        BEGIN;
            THROW 50013, 'EL PRODUCTO NO PERTENECE A ESA VENTA', 1;
        END;

        IF EXISTS (
            SELECT 1 FROM @DETALLES D
            WHERE D.CANTIDAD > (
                SELECT COALESCE(SUM(DV.CANTIDAD), 0)
                FROM DETALLE_VENTAS DV
                WHERE DV.VENTA_ID = @VENTA_ID
                  AND DV.CODIGO_PRODUCTO = D.CODIGOPRODUCTO
            ) - (
                SELECT COALESCE(SUM(DD.CANTIDAD), 0)
                FROM DETALLE_DEVOLUCIONES DD
                INNER JOIN DEVOLUCIONES DV2 ON DV2.ID = DD.DEVOLUCION_ID
                WHERE DV2.VENTA_ID = @VENTA_ID
                  AND DD.CODIGO_PRODUCTO = D.CODIGOPRODUCTO
            )
        )
        BEGIN;
            THROW 50014, 'NO SE PUEDE DEVOLVER MAS DE LO VENDIDO', 1;
        END;

        -- ============ CABECERA DE LA DEVOLUCION ============
        DECLARE @TOTAL DECIMAL(10,2);
        SELECT @TOTAL = SUM(D.CANTIDAD * DV.PRECIO_UNITARIO)
        FROM @DETALLES D
        INNER JOIN DETALLE_VENTAS DV
            ON DV.VENTA_ID = @VENTA_ID AND DV.CODIGO_PRODUCTO = D.CODIGOPRODUCTO;

        INSERT INTO DEVOLUCIONES (VENTA_ID, FECHA, MOTIVO, MONTO_TOTAL)
        VALUES (@VENTA_ID, GETDATE(), COALESCE(@MOTIVO, ''), @TOTAL);

        SET @DEVOLUCION_ID = SCOPE_IDENTITY();

        -- ============ DETALLE + REPOSICION + KARDEX ============
        INSERT INTO DETALLE_DEVOLUCIONES (DEVOLUCION_ID, CODIGO_PRODUCTO, CANTIDAD, SUBTOTAL)
        SELECT @DEVOLUCION_ID, D.CODIGOPRODUCTO, D.CANTIDAD,
               D.CANTIDAD * DV.PRECIO_UNITARIO
        FROM @DETALLES D
        INNER JOIN DETALLE_VENTAS DV
            ON DV.VENTA_ID = @VENTA_ID AND DV.CODIGO_PRODUCTO = D.CODIGOPRODUCTO;

        UPDATE PRODUCTOS
        SET STOCK = STOCK + D.CANTIDAD
        FROM PRODUCTOS P
        INNER JOIN @DETALLES D ON D.CODIGOPRODUCTO = P.CODIGO;

        INSERT INTO MOVIMIENTOS_INVENTARIO (CODIGO_PRODUCTO, TIPO, CANTIDAD, REFERENCIA)
        SELECT CODIGOPRODUCTO, 'devolucion', CANTIDAD, CONCAT('Devolucion #', @DEVOLUCION_ID)
        FROM @DETALLES;

        COMMIT TRANSACTION;
        PRINT 'DEVOLUCION REGISTRADA. MONTO: ' + CAST(@TOTAL AS VARCHAR);

    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        PRINT 'ERROR: ' + ERROR_MESSAGE();
        THROW;
    END CATCH
END
GO
