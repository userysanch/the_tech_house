import json
import re
from datetime import datetime

from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from sqlalchemy import case, func, or_
from extensions import db
from models import (
    Producto, Venta, VentaPendiente, TurnoCaja, MovimientoCaja,
    FormaPago, Cliente, Promocion, Caja,
)

caja_bp = Blueprint('caja', __name__)


def _mensaje_error(e):
    """Extrae el MESSAGE_TEXT de un SIGNAL del stored procedure."""
    m = re.search(r"\(\d+, '([^']+)'\)", str(e))
    return m.group(1) if m else 'No se pudo completar la operacion. Nada se guardo.'


def _turno_abierto():
    return (TurnoCaja.query
            .filter_by(estado='abierto')
            .order_by(TurnoCaja.fecha_apertura.desc())
            .first())


def _saldo_turno(turno):
    delta = (db.session.query(
        func.coalesce(
            func.sum(case(
                (MovimientoCaja.tipo.in_(('ingreso', 'venta')), MovimientoCaja.monto),
                else_=-MovimientoCaja.monto)),
            0))
        .filter(MovimientoCaja.turno_id == turno.id)
        .scalar())
    return float(turno.saldo_inicial) + float(delta)


def _serializar_productos(productos):
    """Lista de resultados con promocion activa aplicada (si existe)."""
    ahora = datetime.utcnow()
    promos = {}
    if productos:
        filas = (Promocion.query
                 .filter(Promocion.activa.is_(True),
                         Promocion.fecha_inicio <= ahora,
                         Promocion.fecha_fin >= ahora,
                         Promocion.codigo_producto.in_([p.codigo for p in productos]))
                 .all())
        promos = {pr.codigo_producto: pr for pr in filas}

    out = []
    for p in productos:
        precio_original = float(p.precio)
        promo = promos.get(p.codigo)
        if promo:
            precio_final = round(precio_original * (1 - float(promo.porcentaje) / 100), 2)
        else:
            precio_final = precio_original
        out.append({
            'id': p.id,
            'codigo': p.codigo,
            'codigo_barras': p.codigo_barras or '',
            'nombre': p.nombre,
            'precio': precio_final,
            'precio_original': precio_original,
            'promo': f'{promo.descripcion} (-{promo.porcentaje}%)' if promo else '',
            'stock': p.stock,
        })
    return out


@caja_bp.route('/', methods=['GET', 'POST'])
@login_required
def caja_view():
    if request.method == 'POST':
        action = request.form.get('action')

        # ---- ABRIR TURNO DE CAJA ----
        if action == 'abrir_turno':
            if _turno_abierto():
                flash('Ya hay un turno abierto. Cierralo antes de abrir otro.', 'warning')
                return redirect(url_for('caja.caja_view'))
            try:
                saldo = round(float(request.form.get('saldo_inicial') or 0), 2)
            except ValueError:
                saldo = -1
            if saldo < 0:
                flash('El saldo inicial no es valido.', 'danger')
                return redirect(url_for('caja.caja_view'))
            caja = Caja.query.order_by(Caja.id).first()
            if not caja:
                flash('No hay ninguna caja configurada (tabla cajas).', 'danger')
                return redirect(url_for('caja.caja_view'))
            turno = TurnoCaja(caja_id=caja.id, usuario_id=current_user.id,
                              saldo_inicial=saldo)
            db.session.add(turno)
            db.session.commit()
            flash(f'Turno #{turno.id} abierto con saldo inicial Q{saldo:.2f}. '
                  'Las ventas del turno quedaran registradas en movimientos de caja.',
                  'success')
            return redirect(url_for('caja.caja_view'))

        # ---- CERRAR TURNO (sp_cerrar_caja) ----
        if action == 'cerrar_turno':
            turno = _turno_abierto()
            if not turno:
                flash('No hay ningun turno abierto.', 'warning')
                return redirect(url_for('caja.caja_view'))
            try:
                db.session.execute(
                    db.text('CALL sp_cerrar_caja(:id)'), {'id': turno.id})
                db.session.commit()
            except Exception as exc:
                db.session.rollback()
                flash(_mensaje_error(exc), 'danger')
                return redirect(url_for('caja.caja_view'))
            turno = db.session.get(TurnoCaja, turno.id)
            n_mov = MovimientoCaja.query.filter_by(turno_id=turno.id).count()
            flash(f'Turno #{turno.id} CERRADO: saldo final '
                  f'Q{float(turno.saldo_final):.2f} ({n_mov} movimiento(s)).',
                  'success')
            return redirect(url_for('caja.caja_view'))

        # ---- MOVIMIENTO MANUAL (ingreso/egreso) ----
        if action == 'movimiento_caja':
            turno = _turno_abierto()
            if not turno:
                flash('Abre primero el turno de caja.', 'danger')
                return redirect(url_for('caja.caja_view'))
            tipo = request.form.get('tipo')
            if tipo not in ('ingreso', 'egreso'):
                flash('Tipo de movimiento invalido.', 'danger')
                return redirect(url_for('caja.caja_view'))
            try:
                monto = round(float(request.form.get('monto') or 0), 2)
            except ValueError:
                monto = -1
            if monto <= 0:
                flash('El monto debe ser mayor a cero.', 'danger')
                return redirect(url_for('caja.caja_view'))
            descripcion = (request.form.get('descripcion') or '').strip()[:150]
            db.session.add(MovimientoCaja(
                turno_id=turno.id, tipo=tipo, monto=monto,
                descripcion=descripcion or tipo.title()))
            db.session.commit()
            flash(f'Movimiento de {tipo} por Q{monto:.2f} registrado en el turno.',
                  'success')
            return redirect(url_for('caja.caja_view'))

    turno = _turno_abierto()
    saldo_actual = _saldo_turno(turno) if turno else None
    movimientos = []
    if turno:
        movimientos = (MovimientoCaja.query
                       .filter_by(turno_id=turno.id)
                       .order_by(MovimientoCaja.fecha.desc())
                       .limit(15)
                       .all())
    formas = FormaPago.query.order_by(FormaPago.id).all()
    clientes = Cliente.query.order_by(Cliente.nombre).all()
    return render_template(
        'caja.html',
        turno=turno,
        saldo_actual=saldo_actual,
        movimientos=movimientos,
        formas=formas,
        clientes=clientes,
        formas_json=[{'id': f.id, 'nombre': f.nombre} for f in formas],
    )


@caja_bp.route('/buscar', methods=['POST'])
@login_required
def buscar_producto():
    data = request.json
    q = data.get('q', '').strip()
    if not q:
        return jsonify([])

    exacto = Producto.query.filter(
        or_(
            Producto.codigo == q,
            Producto.codigo_barras == q
        )
    ).all()

    if exacto:
        return jsonify(_serializar_productos(exacto))

    patron = f'%{q}%'
    resultados = Producto.query.filter(
        or_(
            Producto.codigo.ilike(patron),
            Producto.codigo_barras.ilike(patron),
            Producto.nombre.ilike(patron)
        )
    ).limit(10).all()

    return jsonify(_serializar_productos(resultados))


@caja_bp.route('/registrar', methods=['POST'])
@login_required
def registrar_venta():
    """Alta de venta completa via sp_registrar_venta (transaccion atómica)."""
    data = request.json
    carrito = data.get('carrito', [])
    if not carrito:
        return jsonify({'success': False, 'message': 'El carrito esta vacio.'})

    # Forma de pago: la elegida en el modal o Efectivo por defecto
    forma_pago_id = data.get('forma_pago_id')
    if not forma_pago_id:
        efectivo = FormaPago.query.filter_by(nombre='Efectivo').first()
        forma_pago_id = efectivo.id if efectivo else None

    cliente_id = data.get('cliente_id') or None

    try:
        items = [{
            'codigo': item['codigo'],
            'cantidad': int(item['cantidad']),
            'precio': float(item['precio']),
        } for item in carrito]
    except (KeyError, TypeError, ValueError):
        return jsonify({'success': False, 'message': 'Carrito invalido.'})

    try:
        db.session.execute(db.text('SET @venta_id = 0'))
        db.session.execute(
            db.text('CALL sp_registrar_venta(:cli, :fp, :items, @venta_id)'),
            {'cli': cliente_id, 'fp': forma_pago_id,
             'items': json.dumps(items)}
        )
        venta_id = db.session.execute(db.text('SELECT @venta_id')).scalar()
        db.session.commit()
    except Exception as exc:
        db.session.rollback()
        return jsonify({'success': False, 'message': _mensaje_error(exc)})

    venta = db.session.get(Venta, venta_id)
    total = float(venta.total_venta) if venta else sum(
        i['precio'] * i['cantidad'] for i in items)
    return jsonify({'success': True,
                    'message': f'Venta registrada. Total: Q{total:.2f}',
                    'total': total})


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
