from flask import Blueprint, render_template, request
from flask_login import login_required, current_user
from extensions import db
from models import DetalleVenta, Venta, Producto
from sqlalchemy import func
from datetime import datetime
import calendar

reporte_bp = Blueprint('reporte', __name__)

MESES = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
         'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre']

ANIO_MIN, ANIO_MAX = 2000, 2100


def _entero(valor, minimo, maximo):
    """Convierte un argumento de URL a entero dentro de un rango, o None."""
    try:
        n = int(valor)
    except (TypeError, ValueError):
        return None
    return n if minimo <= n <= maximo else None


@reporte_bp.route('/', methods=['GET', 'POST'])
@login_required
def reporte_view():
    fecha_inicio = request.args.get('fecha_inicio', '')
    fecha_fin = request.args.get('fecha_fin', '')
    anio = _entero(request.args.get('anio', ''), ANIO_MIN, ANIO_MAX)
    mes = _entero(request.args.get('mes', ''), 1, 12)
    if anio is None:
        mes = None  # un mes suelto no tiene sentido sin anio

    query = DetalleVenta.query.join(Venta).order_by(Venta.fecha.desc())
    etiqueta = ''

    if fecha_inicio or fecha_fin:
        # Rango libre: manda sobre anio/mes.
        if fecha_inicio:
            try:
                fi = datetime.strptime(fecha_inicio, '%Y-%m-%d')
                query = query.filter(Venta.fecha >= fi)
            except ValueError:
                pass

        if fecha_fin:
            try:
                ff = datetime.strptime(fecha_fin, '%Y-%m-%d').replace(hour=23, minute=59, second=59)
                query = query.filter(Venta.fecha <= ff)
            except ValueError:
                pass
    elif anio:
        if mes:
            ini = datetime(anio, mes, 1)
            fin = datetime(anio, mes, calendar.monthrange(anio, mes)[1], 23, 59, 59)
            etiqueta = f'{MESES[mes - 1]} {anio}'
        else:
            ini = datetime(anio, 1, 1)
            fin = datetime(anio, 12, 31, 23, 59, 59)
            etiqueta = f'Año {anio}'
        query = query.filter(Venta.fecha >= ini, Venta.fecha <= fin)

    detalles = query.all()

    total_ventas = 0.0
    total_ganancia = 0.0
    reporte_data = []

    for d in detalles:
        total_item = float(d.total)
        ganancia_item = float(d.ganancia)

        total_ventas += total_item
        total_ganancia += ganancia_item

        reporte_data.append({
            'fecha': d.venta.fecha,
            'id': d.producto.id,
            'id_detalle': d.id,
            'codigo': d.codigo_producto,
            'upc': d.producto.codigo_barras or '',
            'producto': d.producto.nombre,
            'cantidad': d.cantidad,
            'total': total_item,
            'ganancia': ganancia_item
        })

    anios = []
    for (y,) in db.session.query(func.year(Venta.fecha)).distinct().all():
        if y:
            anios.append(int(y))
    anios.sort(reverse=True)

    return render_template('reporte.html',
        reporte=reporte_data,
        total_ventas=total_ventas,
        total_ganancia=total_ganancia,
        fecha_inicio=fecha_inicio,
        fecha_fin=fecha_fin,
        anios=anios,
        meses=MESES,
        anio=anio,
        mes=mes,
        etiqueta=etiqueta
    )
