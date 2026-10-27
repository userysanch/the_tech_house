from flask import Blueprint, render_template, request
from flask_login import login_required, current_user
from extensions import db
from models import DetalleVenta, Venta, Producto, Categoria
from sqlalchemy import func, literal_column
from datetime import datetime
import calendar

reporte_bp = Blueprint('reporte', __name__)

# Clave de agrupacion mensual identica en SELECT/GROUP BY/ORDER BY (T-SQL).
MES_KEY = literal_column("CONVERT(VARCHAR(7), ventas.fecha, 120)")

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
    condiciones = []

    if fecha_inicio or fecha_fin:
        # Rango libre: manda sobre anio/mes.
        if fecha_inicio:
            try:
                fi = datetime.strptime(fecha_inicio, '%Y-%m-%d')
                condiciones.append(Venta.fecha >= fi)
            except ValueError:
                pass

        if fecha_fin:
            try:
                ff = datetime.strptime(fecha_fin, '%Y-%m-%d').replace(hour=23, minute=59, second=59)
                condiciones.append(Venta.fecha <= ff)
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
        condiciones.append(Venta.fecha >= ini)
        condiciones.append(Venta.fecha <= fin)

    for cond in condiciones:
        query = query.filter(cond)

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

    # ---- Reportes con funciones de agrupacion (GROUP BY / SUM / COUNT) ----
    # 1) Ventas agrupadas por categoria de producto
    filas_cat = (
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
        .filter(*condiciones)
        .group_by(Categoria.nombre)
        .order_by(func.sum(DetalleVenta.total).desc())
        .all()
    )
    ventas_por_categoria = [
        {'categoria': f[0], 'items': int(f[1]),
         'total': float(f[2]), 'ganancia': float(f[3])}
        for f in filas_cat
    ]

    # 2) Ventas agrupadas por mes (FORMAT ... GROUP BY)
    filas_mes = (
        db.session.query(
            MES_KEY,
            func.count(Venta.id),
            func.coalesce(func.sum(Venta.total_venta), 0),
            func.coalesce(func.sum(Venta.ganancia_total), 0),
        )
        .filter(*condiciones)
        .group_by(MES_KEY)
        .order_by(MES_KEY.desc())
        .all()
    )
    ventas_por_mes = []
    for f in filas_mes:
        anio_mes = f[0] or ''
        try:
            aa, mm = anio_mes.split('-')
            etiqueta_mes = f'{MESES[int(mm) - 1]} {aa}'
        except (ValueError, IndexError):
            etiqueta_mes = anio_mes
        ventas_por_mes.append({
            'clave': anio_mes, 'mes': etiqueta_mes, 'ventas': int(f[1]),
            'total': float(f[2]), 'ganancia': float(f[3]),
        })

    # 3) Top 10 productos mas vendidos (GROUP BY ... ORDER BY ... LIMIT)
    filas_top = (
        db.session.query(
            Producto.codigo,
            Producto.nombre,
            func.sum(DetalleVenta.cantidad),
            func.coalesce(func.sum(DetalleVenta.total), 0),
        )
        .select_from(Producto)
        .join(DetalleVenta, DetalleVenta.codigo_producto == Producto.codigo)
        .join(Venta, Venta.id == DetalleVenta.venta_id)
        .filter(*condiciones)
        .group_by(Producto.codigo, Producto.nombre)
        .order_by(func.sum(DetalleVenta.cantidad).desc())
        .limit(10)
        .all()
    )
    top_productos = [
        {'codigo': f[0], 'nombre': f[1], 'unidades': int(f[2]),
         'total': float(f[3])}
        for f in filas_top
    ]

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
        etiqueta=etiqueta,
        ventas_por_categoria=ventas_por_categoria,
        ventas_por_mes=ventas_por_mes,
        top_productos=top_productos,
    )
