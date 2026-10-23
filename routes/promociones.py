from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user
from datetime import datetime
from sqlalchemy.exc import IntegrityError
from extensions import db
from models import Promocion, Producto

promociones_bp = Blueprint('promociones', __name__)


def _volver():
    return redirect(url_for('promociones.promociones_view'))


@promociones_bp.route('/', methods=['GET', 'POST'])
@login_required
def promociones_view():
    if current_user.rol != 'admin':
        flash('Solo el administrador gestiona las promociones.', 'danger')
        return redirect(url_for('main.index'))

    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'eliminar':
            id_promo = (request.form.get('id') or '').strip()
            try:
                promo = db.session.get(Promocion, int(id_promo))
            except ValueError:
                promo = None
            if not promo:
                flash('La promocion indicada no existe.', 'danger')
                return _volver()
            db.session.delete(promo)
            db.session.commit()
            flash('Promocion eliminada.', 'warning')
            return _volver()

        if action == 'toggle':
            id_promo = (request.form.get('id') or '').strip()
            try:
                promo = db.session.get(Promocion, int(id_promo))
            except ValueError:
                promo = None
            if promo:
                promo.activa = not promo.activa
                db.session.commit()
                flash(f'Promocion {"activada" if promo.activa else "desactivada"}.',
                      'success')
            return _volver()

        # ---- CREAR ----
        codigo = (request.form.get('codigo_producto') or '').strip().upper()
        descripcion = (request.form.get('descripcion') or '').strip()
        porcentaje_raw = (request.form.get('porcentaje') or '').strip()
        inicio_raw = (request.form.get('fecha_inicio') or '').strip()
        fin_raw = (request.form.get('fecha_fin') or '').strip()

        if not codigo or not descripcion:
            flash('Producto y descripcion son obligatorios.', 'danger')
            return _volver()

        producto = Producto.query.filter_by(codigo=codigo).first()
        if not producto:
            flash(f'No existe ningun producto con codigo "{codigo}".', 'danger')
            return _volver()

        try:
            porcentaje = float(porcentaje_raw)
        except ValueError:
            porcentaje = -1
        if not (0 < porcentaje <= 100):
            flash('El porcentaje debe estar entre 0.01 y 100.', 'danger')
            return _volver()

        try:
            fecha_inicio = datetime.strptime(inicio_raw, '%Y-%m-%dT%H:%M')
            fecha_fin = datetime.strptime(fin_raw, '%Y-%m-%dT%H:%M')
        except ValueError:
            flash('Fechas invalidas.', 'danger')
            return _volver()

        if fecha_fin <= fecha_inicio:
            flash('La fecha fin debe ser posterior a la fecha inicio.', 'danger')
            return _volver()

        promo = Promocion(
            codigo_producto=codigo,
            descripcion=descripcion[:150],
            porcentaje=round(porcentaje, 2),
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            activa=True,
        )
        db.session.add(promo)
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            flash('No se pudo guardar (producto inexistente).', 'danger')
            return _volver()
        flash(f'Promocion "{descripcion}" creada: {porcentaje:g}% en '
              f'"{producto.nombre}". Aparecera con descuento en Caja.', 'success')
        return _volver()

    promociones = (Promocion.query
                   .order_by(Promocion.activa.desc(), Promocion.fecha_inicio.desc())
                   .all())
    productos = Producto.query.order_by(Producto.codigo).all()
    ahora = datetime.utcnow().strftime('%Y-%m-%dT%H:%M')
    return render_template('promociones.html', promociones=promociones,
                           productos=productos, ahora=ahora)
