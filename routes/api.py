from functools import wraps

from flask import Blueprint, jsonify, request
from flask_login import current_user
from sqlalchemy import func

from extensions import db
from models import (
    Categoria, Cliente, Devolucion, Entrada, FormaPago, Marca,
    MovimientoInventario, Producto, Proveedor, Venta, DetalleVenta,
)

api_bp = Blueprint('api', __name__, url_prefix='/api')


def _solo_api(f):
    """Las mutaciones exigen sesión; devuelve JSON 401 en vez de redirigir."""
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated:
            return jsonify({'ok': False, 'mensaje': 'Autenticación requerida.'}), 401
        return f(*args, **kwargs)
    return wrapper


def _json(fila):
    return {c.name: getattr(fila, c.name) for c in fila.__table__.columns}


def _error(e):
    return jsonify({'ok': False, 'mensaje': str(e).split('\n')[0]}), 400


# ============================================================
# Catalogos: categorias, marcas, proveedores, clientes, formas_pago
# ============================================================

@api_bp.get('/categorias')
def categorias_lista():
    return jsonify([_json(f) for f in Categoria.query.order_by(Categoria.nombre).all()])


@api_bp.post('/categorias')
@_solo_api
def categorias_crear():
    d = request.get_json(silent=True) or {}
    if not d.get('nombre'):
        return jsonify({'ok': False, 'mensaje': 'El nombre es obligatorio.'}), 400
    if Categoria.query.filter_by(nombre=d['nombre']).first():
        return jsonify({'ok': False, 'mensaje': 'La categoría ya existe.'}), 409
    fila = Categoria(nombre=d['nombre'], descripcion=d.get('descripcion', ''))
    db.session.add(fila)
    db.session.commit()
    return jsonify({'ok': True, 'categoria': _json(fila)}), 201


@api_bp.get('/marcas')
def marcas_lista():
    return jsonify([_json(f) for f in Marca.query.order_by(Marca.nombre).all()])


@api_bp.post('/marcas')
@_solo_api
def marcas_crear():
    d = request.get_json(silent=True) or {}
    if not d.get('nombre'):
        return jsonify({'ok': False, 'mensaje': 'El nombre es obligatorio.'}), 400
    if Marca.query.filter_by(nombre=d['nombre']).first():
        return jsonify({'ok': False, 'mensaje': 'La marca ya existe.'}), 409
    fila = Marca(nombre=d['nombre'])
    db.session.add(fila)
    db.session.commit()
    return jsonify({'ok': True, 'marca': _json(fila)}), 201


@api_bp.get('/proveedores')
def proveedores_lista():
    return jsonify([_json(f) for f in Proveedor.query.order_by(Proveedor.nombre).all()])


@api_bp.post('/proveedores')
@_solo_api
def proveedores_crear():
    d = request.get_json(silent=True) or {}
    if not d.get('nombre'):
        return jsonify({'ok': False, 'mensaje': 'El nombre es obligatorio.'}), 400
    fila = Proveedor(
        nombre=d['nombre'], nit=d.get('nit'), telefono=d.get('telefono'),
        email=d.get('email'), direccion=d.get('direccion'),
    )
    db.session.add(fila)
    db.session.commit()
    return jsonify({'ok': True, 'proveedor': _json(fila)}), 201


@api_bp.get('/clientes')
def clientes_lista():
    return jsonify([_json(f) for f in Cliente.query.order_by(Cliente.nombre).all()])


@api_bp.post('/clientes')
@_solo_api
def clientes_crear():
    d = request.get_json(silent=True) or {}
    if not d.get('nombre'):
        return jsonify({'ok': False, 'mensaje': 'El nombre es obligatorio.'}), 400
    fila = Cliente(
        nombre=d['nombre'], nit=d.get('nit'), telefono=d.get('telefono'),
        email=d.get('email'), direccion=d.get('direccion'),
    )
    db.session.add(fila)
    db.session.commit()
    return jsonify({'ok': True, 'cliente': _json(fila)}), 201


@api_bp.get('/formas-pago')
def formas_pago_lista():
    return jsonify([_json(f) for f in FormaPago.query.order_by(FormaPago.id).all()])


# ============================================================
# Productos (CRUD)
# ============================================================

@api_bp.get('/productos')
def productos_lista():
    q = request.args.get('q', '').strip()
    query = Producto.query
    if q:
        like = f'%{q}%'
        query = query.filter(db.or_(Producto.nombre.like(like),
                                    Producto.codigo.like(like),
                                    Producto.codigo_barras.like(like)))
    return jsonify([_json(p) for p in query.order_by(Producto.nombre).all()])


@api_bp.get('/productos/<codigo>')
def productos_detalle(codigo):
    p = Producto.query.filter_by(codigo=codigo).first()
    if not p:
        return jsonify({'ok': False, 'mensaje': 'Producto no encontrado.'}), 404
    return jsonify(_json(p))


@api_bp.post('/productos')
@_solo_api
def productos_crear():
    d = request.get_json(silent=True) or {}
    if not d.get('codigo') or not d.get('nombre'):
        return jsonify({'ok': False, 'mensaje': 'codigo y nombre son obligatorios.'}), 400
    if Producto.query.filter_by(codigo=d['codigo']).first():
        return jsonify({'ok': False, 'mensaje': 'El código ya existe.'}), 409
    p = Producto(
        codigo=d['codigo'], nombre=d['nombre'],
        costo=d.get('costo', 0), margen=d.get('margen', 0),
        precio=d.get('precio', 0), stock=d.get('stock', 0),
        codigo_barras=d.get('codigo_barras'),
        categoria_id=d.get('categoria_id'), marca_id=d.get('marca_id'),
        proveedor_id=d.get('proveedor_id'),
    )
    db.session.add(p)
    db.session.commit()
    return jsonify({'ok': True, 'producto': _json(p)}), 201


@api_bp.put('/productos/<codigo>')
@_solo_api
def productos_actualizar(codigo):
    p = Producto.query.filter_by(codigo=codigo).first()
    if not p:
        return jsonify({'ok': False, 'mensaje': 'Producto no encontrado.'}), 404
    d = request.get_json(silent=True) or {}
    for campo in ('nombre', 'costo', 'margen', 'precio', 'stock', 'codigo_barras',
                  'categoria_id', 'marca_id', 'proveedor_id'):
        if campo in d:
            setattr(p, campo, d[campo])
    db.session.commit()
    return jsonify({'ok': True, 'producto': _json(p)})


@api_bp.delete('/productos/<codigo>')
@_solo_api
def productos_eliminar(codigo):
    p = Producto.query.filter_by(codigo=codigo).first()
    if not p:
        return jsonify({'ok': False, 'mensaje': 'Producto no encontrado.'}), 404
    if p.detalles:
        return jsonify({'ok': False,
                        'mensaje': 'No se puede eliminar: tiene ventas registradas.'}), 409
    db.session.delete(p)
    db.session.commit()
    return jsonify({'ok': True, 'mensaje': 'Producto eliminado.'})


# ============================================================
# Entradas de mercancia (transaccion: entrada + stock + kardex)
# ============================================================

@api_bp.get('/entradas')
def entradas_lista():
    return jsonify([_json(e) for e in Entrada.query.order_by(Entrada.fecha.desc()).all()])


@api_bp.post('/entradas')
@_solo_api
def entradas_crear():
    d = request.get_json(silent=True) or {}
    codigo = d.get('codigo_producto')
    cantidad = int(d.get('cantidad') or 0)
    if not codigo or cantidad <= 0:
        return jsonify({'ok': False, 'mensaje': 'codigo_producto y cantidad>0 requeridos.'}), 400
    p = Producto.query.filter_by(codigo=codigo).first()
    if not p:
        return jsonify({'ok': False, 'mensaje': 'Producto no existe.'}), 404
    try:
        e = Entrada(codigo_producto=codigo, cantidad=cantidad,
                    costo_unitario=d.get('costo_unitario', p.costo),
                    upc=d.get('upc'), proveedor_id=d.get('proveedor_id'))
        db.session.add(e)
        p.stock = (p.stock or 0) + cantidad
        if d.get('costo_unitario') is not None:
            p.costo = d['costo_unitario']
        db.session.add(MovimientoInventario(codigo_producto=codigo, tipo='entrada',
                                            cantidad=cantidad,
                                            referencia=f"Entrada de mercancía"))
        db.session.commit()
    except Exception as exc:
        db.session.rollback()
        return _error(exc)
    return jsonify({'ok': True, 'entrada': _json(e), 'stock': p.stock}), 201


# ============================================================
# Ventas: listado y alta via SP_REGISTRARVENTA (transaccional)
# ============================================================

@api_bp.get('/ventas')
def ventas_lista():
    filas = Venta.query.order_by(Venta.fecha.desc()).limit(200).all()
    out = []
    for v in filas:
        item = _json(v)
        item['detalles'] = [_json(d) for d in v.detalles]
        item['pagos'] = [_json(pg) for pg in v.pagos]
        out.append(item)
    return jsonify(out)


@api_bp.post('/ventas')
@_solo_api
def ventas_crear():
    d = request.get_json(silent=True) or {}
    items = d.get('items') or []
    if not items:
        return jsonify({'ok': False, 'mensaje': 'La venta no tiene items.'}), 400
    import json as _json_mod
    try:
        db.session.execute(db.text('SET @venta_id = 0'))
        db.session.execute(
            db.text('CALL SP_REGISTRARVENTA(:cli, :fp, :items, @venta_id)'),
            {'cli': d.get('cliente_id'), 'fp': d.get('forma_pago_id'),
             'items': _json_mod.dumps(items)}
        )
        venta_id = db.session.execute(db.text('SELECT @venta_id')).scalar()
        db.session.commit()
    except Exception as exc:
        db.session.rollback()
        return _error(exc)
    v = Venta.query.get(venta_id)
    return jsonify({'ok': True, 'venta': _json(v),
                    'detalles': [_json(x) for x in v.detalles]}), 201


@api_bp.post('/devoluciones')
@_solo_api
def devoluciones_crear():
    d = request.get_json(silent=True) or {}
    items = d.get('items') or []
    if not items or not d.get('venta_id'):
        return jsonify({'ok': False, 'mensaje': 'venta_id e items requeridos.'}), 400
    import json as _json_mod
    try:
        db.session.execute(db.text('SET @dev_id = 0'))
        db.session.execute(
            db.text('CALL SP_APLICARDEVOLUCION(:vid, :motivo, :items, @dev_id)'),
            {'vid': d['venta_id'], 'motivo': d.get('motivo', ''),
             'items': _json_mod.dumps(items)}
        )
        dev_id = db.session.execute(db.text('SELECT @dev_id')).scalar()
        db.session.commit()
    except Exception as exc:
        db.session.rollback()
        return _error(exc)
    dev = Devolucion.query.get(dev_id)
    return jsonify({'ok': True, 'devolucion': _json(dev),
                    'detalles': [_json(x) for x in dev.detalles]}), 201


# ============================================================
# Reportes con funciones de agrupacion (GROUP BY / SUM / COUNT)
# ============================================================

@api_bp.get('/reporte/ventas-por-categoria')
def reporte_ventas_por_categoria():
    filas = (
        db.session.query(
            Categoria.nombre,
            func.count(DetalleVenta.id),
            func.coalesce(func.sum(DetalleVenta.total), 0),
            func.coalesce(func.sum(DetalleVenta.ganancia), 0),
        )
        .select_from(Categoria)
        .join(Producto, Producto.categoria_id == Categoria.id)
        .join(DetalleVenta, DetalleVenta.codigo_producto == Producto.codigo)
        .join(Venta, Venta.id == DetalleVenta.venta_id)
        .group_by(Categoria.nombre)
        .order_by(func.sum(DetalleVenta.total).desc())
        .all()
    )
    return jsonify([
        {'categoria': f[0], 'items_vendidos': int(f[1]),
         'total_ventas': float(f[2]), 'ganancia': float(f[3])}
        for f in filas
    ])


@api_bp.get('/reporte/ventas-por-mes')
def reporte_ventas_por_mes():
    filas = (
        db.session.query(
            func.date_format(Venta.fecha, '%Y-%m'),
            func.count(Venta.id),
            func.coalesce(func.sum(Venta.total_venta), 0),
            func.coalesce(func.sum(Venta.ganancia_total), 0),
        )
        .group_by(func.date_format(Venta.fecha, '%Y-%m'))
        .order_by(func.date_format(Venta.fecha, '%Y-%m').desc())
        .all()
    )
    return jsonify([
        {'mes': f[0], 'ventas': int(f[1]),
         'total': float(f[2]), 'ganancia': float(f[3])}
        for f in filas
    ])


@api_bp.get('/reporte/top-productos')
def reporte_top_productos():
    filas = (
        db.session.query(
            Producto.codigo,
            Producto.nombre,
            func.sum(DetalleVenta.cantidad),
            func.coalesce(func.sum(DetalleVenta.total), 0),
        )
        .join(DetalleVenta, DetalleVenta.codigo_producto == Producto.codigo)
        .group_by(Producto.codigo, Producto.nombre)
        .order_by(func.sum(DetalleVenta.cantidad).desc())
        .limit(10)
        .all()
    )
    return jsonify([
        {'codigo': f[0], 'nombre': f[1], 'unidades': int(f[2]),
         'total': float(f[3])}
        for f in filas
    ])
