"""Llamadas a los procedimientos almacenados T-SQL de SQL Server.

Los SP reciben un tipo de tabla TVP (@DETALLES) en vez de JSON: aqui
construimos la variable de tabla con INSERT ... VALUES y ejecutamos el SP
con el parametro OUTPUT devuelto mediante un SELECT final del mismo lote.
"""
from extensions import db


def _valores_tvp(items, incluye_precio):
    vals, params = [], {}
    for i, it in enumerate(items):
        if incluye_precio:
            vals.append(f"(:c{i}, :q{i}, :p{i})")
            params[f'p{i}'] = float(it['precio'])
        else:
            vals.append(f"(:c{i}, :q{i}, NULL)")
        params[f'c{i}'] = it['codigo']
        params[f'q{i}'] = int(it['cantidad'])
    return ', '.join(vals), params


def registrar_venta(cliente_id, forma_pago_id, items):
    """items: [{'codigo', 'cantidad', 'precio'}] -> id de la venta creada."""
    valores, params = _valores_tvp(items, True)
    params['cli'] = cliente_id
    params['fp'] = forma_pago_id
    sql = f"""
        SET NOCOUNT ON;
        DECLARE @d TIPODETALLEVENTA;
        INSERT INTO @d (CODIGOPRODUCTO, CANTIDAD, PRECIO)
        VALUES {valores};
        DECLARE @out INT;
        EXEC SP_REGISTRARVENTA @CLIENTE_ID = :cli, @FORMA_PAGOID = :fp,
             @DETALLES = @d, @VENTA_ID = @out OUTPUT;
        SELECT @out AS id;
    """
    return int(db.session.execute(db.text(sql), params).scalar())


def aplicar_devolucion(venta_id, motivo, items):
    """items: [{'codigo', 'cantidad'}] -> id de la devolucion creada."""
    valores, params = _valores_tvp(items, False)
    params['vid'] = venta_id
    params['motivo'] = motivo or ''
    sql = f"""
        SET NOCOUNT ON;
        DECLARE @d TIPODETALLEVENTA;
        INSERT INTO @d (CODIGOPRODUCTO, CANTIDAD, PRECIO)
        VALUES {valores};
        DECLARE @out INT;
        EXEC SP_APLICARDEVOLUCION @VENTA_ID = :vid, @MOTIVO = :motivo,
             @DETALLES = @d, @DEVOLUCION_ID = @out OUTPUT;
        SELECT @out AS id;
    """
    return int(db.session.execute(db.text(sql), params).scalar())


def cerrar_caja(turno_id):
    """Ejecuta SP_CERRARCAJA; lanza excepcion si el turno no esta abierto."""
    db.session.execute(
        db.text('SET NOCOUNT ON; EXEC SP_CERRARCAJA @TURNO_ID = :id;'),
        {'id': turno_id})
