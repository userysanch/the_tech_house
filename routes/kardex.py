from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user
from models import MovimientoInventario

kardex_bp = Blueprint('kardex', __name__)

TIPOS = {
    'entrada': ('Entradas', 'badge-dp-success'),
    'salida': ('Salidas', 'badge-dp-primary'),
    'ajuste': ('Ajustes', 'badge-dp-warning'),
    'devolucion': ('Devoluciones', 'badge-dp-danger'),
}


@kardex_bp.route('/')
@login_required
def kardex_view():
    if current_user.rol != 'admin':
        flash('Solo el administrador puede consultar el kardex.', 'danger')
        return redirect(url_for('main.index'))

    tipo = (request.args.get('tipo') or '').strip()
    query = MovimientoInventario.query
    if tipo in TIPOS:
        query = query.filter_by(tipo=tipo)
    else:
        tipo = 'todos'

    movimientos = (query
                   .order_by(MovimientoInventario.fecha.desc(),
                             MovimientoInventario.id.desc())
                   .limit(500)
                   .all())

    # Totales por tipo (GROUP BY) para el resumen superior
    from sqlalchemy import func
    resumen = dict(
        MovimientoInventario.query
        .with_entities(MovimientoInventario.tipo, func.count(MovimientoInventario.id))
        .group_by(MovimientoInventario.tipo)
        .all()
    )

    return render_template('kardex.html', movimientos=movimientos,
                           tipo=tipo, tipos=TIPOS, resumen=resumen)
