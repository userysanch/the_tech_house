from flask import Blueprint, render_template
from flask_login import login_required, current_user
from extensions import db
from models import Producto, Venta, DetalleVenta
from datetime import datetime, date

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
@login_required
def index():
    from sqlalchemy import func

    total_productos = Producto.query.count()
    stock_bajo = Producto.query.filter(Producto.stock < 5).count()

    hoy = date.today()
    ventas_hoy = db.session.query(func.coalesce(func.sum(Venta.total_venta), 0)).filter(
        db.func.date(Venta.fecha) == hoy
    ).scalar()
    ganancia_hoy = db.session.query(func.coalesce(func.sum(Venta.ganancia_total), 0)).filter(
        db.func.date(Venta.fecha) == hoy
    ).scalar()

    return render_template('index.html',
        total_productos=total_productos,
        stock_bajo=stock_bajo,
        ventas_hoy=float(ventas_hoy),
        ganancia_hoy=float(ganancia_hoy)
    )
