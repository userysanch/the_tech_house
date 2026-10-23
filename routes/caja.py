from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from extensions import db
from models import Producto, Venta, DetalleVenta, VentaPendiente
from datetime import datetime

caja_bp = Blueprint('caja', __name__)

@caja_bp.route('/')
@login_required
def caja_view():
    return render_template('caja.html')

@caja_bp.route('/buscar', methods=['POST'])
@login_required
def buscar_producto():
    data = request.json
    q = data.get('q', '').strip()
    if not q:
        return jsonify([])

    from sqlalchemy import or_

    exacto = Producto.query.filter(
        or_(
            Producto.codigo == q,
            Producto.codigo_barras == q
        )
    ).all()

    if exacto:
        return jsonify([{
            'id': p.id,
            'codigo': p.codigo,
            'codigo_barras': p.codigo_barras or '',
            'nombre': p.nombre,
            'precio': float(p.precio),
            'stock': p.stock
        } for p in exacto])

    patron = f'%{q}%'
    resultados = Producto.query.filter(
        or_(
            Producto.codigo.ilike(patron),
            Producto.codigo_barras.ilike(patron),
            Producto.nombre.ilike(patron)
        )
    ).limit(10).all()

    return jsonify([{
        'id': p.id,
        'codigo': p.codigo,
        'codigo_barras': p.codigo_barras or '',
        'nombre': p.nombre,
        'precio': float(p.precio),
        'stock': p.stock
    } for p in resultados])

@caja_bp.route('/registrar', methods=['POST'])
@login_required
def registrar_venta():
    data = request.json
    carrito = data.get('carrito', [])
    if not carrito:
        return jsonify({'success': False, 'message': 'El carrito esta vacio.'})
    total_venta = 0
    ganancia_total = 0
    nueva_venta = Venta(fecha=datetime.utcnow(), total_venta=0, ganancia_total=0)
    db.session.add(nueva_venta)
    db.session.flush()
    for item in carrito:
        producto = Producto.query.filter_by(codigo=item['codigo']).first()
        if not producto or producto.stock < item['cantidad']:
            db.session.rollback()
            return jsonify({'success': False, 'message': f'Stock insuficiente para {item["codigo"]}'})
        cantidad = int(item['cantidad'])
        precio_unitario = float(item['precio'])
        total_item = cantidad * precio_unitario
        ganancia_item = (precio_unitario - float(producto.costo)) * cantidad
        detalle = DetalleVenta(
            venta_id=nueva_venta.id,
            codigo_producto=producto.codigo,
            cantidad=cantidad,
            precio_unitario=precio_unitario,
            total=total_item,
            ganancia=ganancia_item
        )
        db.session.add(detalle)
        producto.stock -= cantidad
        total_venta += total_item
        ganancia_total += ganancia_item
    nueva_venta.total_venta = total_venta
    nueva_venta.ganancia_total = ganancia_total
    db.session.commit()
    return jsonify({'success': True, 'message': f'Venta registrada. Total: Q{total_venta:.2f}'})

@caja_bp.route('/api/poll-carrito', methods=['GET'])
@login_required
def api_poll_carrito():
    pendientes = VentaPendiente.query.filter_by(estado='pendiente').all()
    items = []
    for p in pendientes:
        items.append({
            'id': p.id,
            'codigo': p.producto_codigo,
            'nombre': p.producto_nombre,
            'cantidad': p.cantidad,
            'precio': float(p.precio_unitario),
            'total': float(p.total)
        })
        p.estado = 'agregado'
    db.session.commit()
    return jsonify(items)
