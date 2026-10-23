from decimal import Decimal

from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user
from extensions import db
from models import DetalleVenta, Venta, Producto

ventas_bp = Blueprint('ventas', __name__)


def _volver():
    """Regresa a la pagina que origino la peticion (solo rutas internas)."""
    destino = (request.form.get('next') or '').strip()
    if destino.startswith('/') and not destino.startswith('//'):
        return redirect(destino)
    return redirect(url_for('ventas.ventas_view'))


@ventas_bp.route('/', methods=['GET', 'POST'])
@login_required
def ventas_view():
    if request.method == 'POST' and request.form.get('action') == 'anular_venta':
        if current_user.rol != 'admin':
            flash('Solo el administrador puede anular ventas.', 'danger')
            return redirect(url_for('main.index'))

        id_detalle = request.form.get('id_detalle')
        detalle = DetalleVenta.query.get(id_detalle) if id_detalle else None
        if not detalle:
            flash('La venta indicada no existe.', 'danger')
            return _volver()

        venta = Venta.query.get(detalle.venta_id)
        producto = Producto.query.filter_by(codigo=detalle.codigo_producto).first()
        if producto:
            producto.stock += int(detalle.cantidad)

        if venta:
            venta.total_venta = max(Decimal('0.00'), venta.total_venta - detalle.total)
            venta.ganancia_total = max(Decimal('0.00'), venta.ganancia_total - detalle.ganancia)

        unidades = int(detalle.cantidad)
        nombre_prod = producto.nombre if producto else detalle.codigo_producto
        era_unica = DetalleVenta.query.filter_by(venta_id=detalle.venta_id).count() <= 1

        db.session.delete(detalle)
        if venta and era_unica:
            db.session.delete(venta)
        db.session.commit()

        mensaje = (f'Venta anulada: {unidades} unidad(es) de "{nombre_prod}" '
                   f'devuelta(s) al inventario.')
        if producto:
            mensaje += f' Stock en Inventario: {producto.stock}.'
        flash(mensaje, 'warning')
        return _volver()

    detalles = DetalleVenta.query.join(Venta).order_by(Venta.fecha.desc()).all()
    return render_template('ventas.html', detalles=detalles)
