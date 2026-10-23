from flask import Blueprint, render_template, jsonify, request
from flask_login import login_required
from models import Producto, Venta, DetalleVenta, VentaPendiente
from datetime import datetime
from extensions import db

scanner_bp = Blueprint('scanner', __name__)

@scanner_bp.route('/')
@login_required
def scanner_view():
    return render_template('scanner.html')

@scanner_bp.route('/api/lookup', methods=['POST'])
@login_required
def api_lookup():
    codigo = request.json.get('codigo', '').strip()
    if not codigo:
        return jsonify({'encontrado': False})
    producto = Producto.query.filter(
        (Producto.codigo == codigo) | (Producto.codigo_barras == codigo)
    ).first()
    if not producto:
        return jsonify({'encontrado': False})
    return jsonify({
        'encontrado': True,
        'id': producto.id,
        'codigo': producto.codigo,
        'nombre': producto.nombre,
        'precio': float(producto.precio),
        'stock': producto.stock,
        'costo': float(producto.costo),
        'codigo_barras': producto.codigo_barras or ''
    })

@scanner_bp.route('/api/products', methods=['GET'])
@login_required
def api_products():
    productos = Producto.query.order_by(Producto.nombre).all()
    return jsonify([{
        'id': p.id,
        'codigo': p.codigo,
        'nombre': p.nombre,
        'precio': float(p.precio),
        'stock': p.stock,
        'codigo_barras': p.codigo_barras
    } for p in productos])

@scanner_bp.route('/api/assign-barcode', methods=['POST'])
@login_required
def api_assign_barcode():
    data = request.json
    producto_id = data.get('producto_id')
    barcode = data.get('barcode', '').strip()
    if not producto_id or not barcode:
        return jsonify({'success': False, 'message': 'Datos incompletos'})
    existing = Producto.query.filter_by(codigo_barras=barcode).first()
    if existing and existing.id != producto_id:
        return jsonify({'success': False, 'message': f'Este codigo ya pertenece a {existing.nombre}'})
    producto = Producto.query.get(producto_id)
    if not producto:
        return jsonify({'success': False, 'message': 'Producto no encontrado'})
    producto.codigo_barras = barcode
    db.session.commit()
    return jsonify({'success': True, 'message': f'Codigo asignado a {producto.nombre}'})

@scanner_bp.route('/api/add-to-cart', methods=['POST'])
@login_required
def api_add_to_cart():
    data = request.json
    codigo = data.get('codigo', '').strip()
    cantidad = int(data.get('cantidad', 1))
    producto = Producto.query.filter(
        (Producto.codigo == codigo) | (Producto.codigo_barras == codigo)
    ).first()
    if not producto:
        return jsonify({'success': False, 'message': 'Producto no encontrado'})
    if producto.stock < cantidad:
        return jsonify({'success': False, 'message': f'Stock insuficiente. Solo hay {producto.stock} unidades'})
    celular_ip = request.remote_addr
    pendiente = VentaPendiente(
        scanner_code=codigo,
        producto_codigo=producto.codigo,
        producto_nombre=producto.nombre,
        cantidad=cantidad,
        precio_unitario=float(producto.precio),
        total=float(producto.precio) * cantidad,
        celular_ip=celular_ip,
        estado='pendiente'
    )
    db.session.add(pendiente)
    db.session.commit()
    return jsonify({
        'success': True,
        'message': f'Enviado a Caja: {producto.nombre} x{cantidad}',
        'total': float(producto.precio) * cantidad,
        'pendiente_id': pendiente.id
    })
