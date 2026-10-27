import json
import re

from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user
from extensions import db
from models import (
    Venta, DetalleVenta, Devolucion, DetalleDevolucion,
)

devoluciones_bp = Blueprint('devoluciones', __name__)


def _mensaje_error(e):
    m = re.search(r"\(\d+, '([^']+)'\)", str(e))
    return m.group(1) if m else 'No se pudo registrar la devolucion. Nada se guardo.'


def _devueltas(venta_id, codigo):
    """Unidades ya devueltos de un producto en una venta."""
    from sqlalchemy import func
    return int(db.session.query(
        func.coalesce(func.sum(DetalleDevolucion.cantidad), 0))
        .join(Devolucion, Devolucion.id == DetalleDevolucion.devolucion_id)
        .filter(Devolucion.venta_id == venta_id,
                DetalleDevolucion.codigo_producto == codigo)
        .scalar() or 0)


@devoluciones_bp.route('/', methods=['GET', 'POST'])
@login_required
def devoluciones_view():
    if current_user.rol != 'admin':
        flash('Solo el administrador puede registrar devoluciones.', 'danger')
        return redirect(url_for('main.index'))

    if request.method == 'POST':
        venta_id = (request.form.get('venta_id') or '').strip()
        motivo = (request.form.get('motivo') or '').strip()[:200]
        try:
            venta_id = int(venta_id)
        except ValueError:
            flash('Venta invalida.', 'danger')
            return redirect(url_for('devoluciones.devoluciones_view'))

        venta = db.session.get(Venta, venta_id)
        if not venta:
            flash('La venta indicada no existe.', 'danger')
            return redirect(url_for('devoluciones.devoluciones_view'))

        # Construir items validando cantidades contra lo vendido
        codigos = request.form.getlist('codigo')
        cantidades = request.form.getlist('cantidad')
        items = []
        for cod, cant in zip(codigos, cantidades):
            cod = (cod or '').strip()
            try:
                q = int(cant or 0)
            except ValueError:
                q = 0
            if not cod or q <= 0:
                continue
            vendidas = sum(int(d.cantidad) for d in venta.detalles
                           if d.codigo_producto == cod)
            ya_dev = _devueltas(venta.id, cod)
            disponibles = vendidas - ya_dev
            if q > disponibles:
                flash(f'"{cod}": solo puedes devolver {disponibles} unidad(es) '
                      f'(vendidas {vendidas}, ya devueltas {ya_dev}).', 'danger')
                return redirect(url_for('devoluciones.devoluciones_view',
                                        venta_id=venta.id))
            items.append({'codigo': cod, 'cantidad': q})

        if not items:
            flash('Indica la cantidad a devolver de al menos un producto.', 'danger')
            return redirect(url_for('devoluciones.devoluciones_view',
                                    venta_id=venta.id))

        try:
            db.session.execute(db.text('SET @dev_id = 0'))
            db.session.execute(
                db.text('CALL SP_APLICARDEVOLUCION(:vid, :motivo, :items, @dev_id)'),
                {'vid': venta.id, 'motivo': motivo or 'Devolucion desde pantalla',
                 'items': json.dumps(items)}
            )
            db.session.execute(db.text('SELECT @dev_id')).scalar()
            db.session.commit()
        except Exception as exc:
            db.session.rollback()
            flash(_mensaje_error(exc), 'danger')
            return redirect(url_for('devoluciones.devoluciones_view',
                                    venta_id=venta.id))

        flash('Devolucion registrada: el stock repuso las unidades y el kardex '
              'queda actualizado.', 'success')
        return redirect(url_for('devoluciones.devoluciones_view'))

    # Venta seleccionada (para armar la devolucion)
    venta = None
    venta_id = (request.args.get('venta_id') or '').strip()
    if venta_id.isdigit():
        venta = db.session.get(Venta, int(venta_id))

    ventas = (Venta.query
              .order_by(Venta.fecha.desc())
              .limit(30)
              .all())

    # Detalle de las devoluciones existentes (con sus items)
    devoluciones = (Devolucion.query
                    .order_by(Devolucion.fecha.desc())
                    .limit(30)
                    .all())

    # Cantidades ya devueltas por venta para mostrar en la pantalla
    devueltas = {}
    for d in devoluciones:
        for det in d.detalles:
            clave = (d.venta_id, det.codigo_producto)
            devueltas[clave] = devueltas.get(clave, 0) + int(det.cantidad)

    return render_template('devoluciones.html',
                           ventas=ventas, venta=venta,
                           devoluciones=devoluciones, devueltas=devueltas)
