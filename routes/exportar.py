from io import BytesIO
from datetime import datetime
import calendar

from flask import (Blueprint, current_app, flash, redirect, request,
                   send_file, url_for)
from flask_login import current_user, login_required
from sqlalchemy import or_

from extensions import db
from models import DetalleVenta, Entrada, Producto, Venta
from routes.reporte import ANIO_MAX, ANIO_MIN, _entero

exportar_bp = Blueprint('exportar', __name__)

XLSX_MIME = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'

# clave de URL -> (archivo descargado, funcion que arma la hoja, pagina de vuelta)
HOJAS = {}


def _volver(hoja):
    """Regresa a la pagina que origino la exportacion, conservando filtros."""
    if hoja == 'ganancias':
        filtros = {k: request.args.get(k) for k in
                   ('anio', 'mes', 'fecha_inicio', 'fecha_fin')
                   if request.args.get(k)}
        if filtros:
            return redirect(url_for('reporte.reporte_view', **filtros))
    vistas = {'productos': 'inventario.inventario_view',
              'compras': 'entrada.entrada_view',
              'ventas': 'ventas.ventas_view',
              'ganancias': 'reporte.reporte_view'}
    if hoja in vistas:
        return redirect(url_for(vistas[hoja]))
    return redirect(url_for('main.index'))


def _libro(titulo, encabezados, filas, anchos):
    """Arma un .xlsx con el mismo estilo del export de Registros."""
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    from openpyxl.utils import get_column_letter

    wb = Workbook()
    ws = wb.active
    ws.title = titulo

    relleno = PatternFill(start_color='FE9F43', end_color='FE9F43',
                          fill_type='solid')
    fuente = Font(bold=True, color='FFFFFF', size=11)
    borde = Border(
        left=Side(style='thin', color='DDDDDD'),
        right=Side(style='thin', color='DDDDDD'),
        top=Side(style='thin', color='DDDDDD'),
        bottom=Side(style='thin', color='DDDDDD'),
    )
    centro = Alignment(horizontal='center', vertical='center')

    for col, titulo_col in enumerate(encabezados, start=1):
        celda = ws.cell(row=1, column=col, value=titulo_col)
        celda.fill = relleno
        celda.font = fuente
        celda.alignment = centro
        celda.border = borde

    for fila_n, datos in enumerate(filas, start=2):
        for col, valor in enumerate(datos, start=1):
            celda = ws.cell(row=fila_n, column=col, value=valor)
            celda.border = borde
            if isinstance(valor, datetime):
                celda.number_format = 'dd/mm/yyyy hh:mm'

    for col, ancho in enumerate(anchos, start=1):
        ws.column_dimensions[get_column_letter(col)].width = ancho

    if filas:
        ultima = get_column_letter(len(encabezados))
        ws.auto_filter.ref = f'A1:{ultima}{len(filas) + 1}'
    ws.freeze_panes = 'A2'
    return wb


# ---------------------------------------------------------------- hojas ----

def _productos():
    """Misma consulta que la pagina de Inventario."""
    productos = (Producto.query
                 .outerjoin(Entrada, Entrada.codigo_producto == Producto.codigo)
                 .filter(or_(Producto.stock > 0, Entrada.id.isnot(None)))
                 .distinct()
                 .order_by(Producto.id.asc())
                 .all())

    encabezados = ['#', 'UPC', 'Codigo', 'Producto', 'Costo', 'Margen %',
                   'Precio Venta', 'Stock']
    filas = []
    for i, p in enumerate(productos, start=1):
        filas.append([i, p.codigo_barras or '', p.codigo, p.nombre,
                      p.costo, p.margen, p.precio, p.stock])
    return ('Productos', encabezados, filas,
            [6, 22, 20, 70, 14, 12, 16, 10])


def _compras():
    entradas = Entrada.query.order_by(Entrada.fecha.desc()).all()

    encabezados = ['Fecha', 'UPC', 'Codigo', 'Producto', 'Cantidad',
                   'Costo Unit.', 'Total']
    filas = []
    for e in entradas:
        prod = e.producto
        filas.append([e.fecha, e.upc or '', e.codigo_producto,
                      prod.nombre if prod else '', e.cantidad,
                      e.costo_unitario, e.cantidad * e.costo_unitario])
    return ('Compras', encabezados, filas, [20, 22, 20, 70, 12, 14, 16])


def _ventas():
    detalles = DetalleVenta.query.join(Venta).order_by(Venta.fecha.desc()).all()

    encabezados = ['Fecha', 'UPC', 'Codigo', 'Producto', 'Cantidad', 'Total']
    filas = []
    for d in detalles:
        prod = d.producto
        filas.append([d.venta.fecha, (prod.codigo_barras if prod else '') or '',
                      d.codigo_producto, prod.nombre if prod else '',
                      d.cantidad, d.total])
    return ('Ventas', encabezados, filas, [20, 22, 20, 70, 12, 16])


def _ganancias():
    """Respeta los mismos filtros de la pagina de Ganancias."""
    fecha_inicio = request.args.get('fecha_inicio', '')
    fecha_fin = request.args.get('fecha_fin', '')
    anio = _entero(request.args.get('anio', ''), ANIO_MIN, ANIO_MAX)
    mes = _entero(request.args.get('mes', ''), 1, 12)
    if anio is None:
        mes = None

    query = DetalleVenta.query.join(Venta).order_by(Venta.fecha.desc())

    if fecha_inicio or fecha_fin:
        if fecha_inicio:
            try:
                fi = datetime.strptime(fecha_inicio, '%Y-%m-%d')
                query = query.filter(Venta.fecha >= fi)
            except ValueError:
                pass
        if fecha_fin:
            try:
                ff = (datetime.strptime(fecha_fin, '%Y-%m-%d')
                      .replace(hour=23, minute=59, second=59))
                query = query.filter(Venta.fecha <= ff)
            except ValueError:
                pass
    elif anio:
        if mes:
            ini = datetime(anio, mes, 1)
            fin = datetime(anio, mes, calendar.monthrange(anio, mes)[1],
                           23, 59, 59)
        else:
            ini = datetime(anio, 1, 1)
            fin = datetime(anio, 12, 31, 23, 59, 59)
        query = query.filter(Venta.fecha >= ini, Venta.fecha <= fin)

    encabezados = ['Fecha', 'UPC', 'Codigo', 'Producto', 'Cantidad',
                   'Total Venta', 'Ganancia']
    filas = []
    for d in query.all():
        prod = d.producto
        filas.append([d.venta.fecha, (prod.codigo_barras if prod else '') or '',
                      d.codigo_producto, prod.nombre if prod else '',
                      d.cantidad, d.total, d.ganancia])
    return ('Ganancias', encabezados, filas, [20, 22, 20, 70, 12, 16, 16])


HOJAS = {
    'productos': ('productos_tech_house.xlsx', _productos),
    'compras': ('compras_tech_house.xlsx', _compras),
    'ventas': ('ventas_tech_house.xlsx', _ventas),
    'ganancias': ('ganancias_tech_house.xlsx', _ganancias),
}


@exportar_bp.route('/excel/<hoja>')
@login_required
def exportar_excel(hoja):
    if current_user.rol != 'admin':
        flash('Solo el administrador puede exportar los datos.', 'danger')
        return redirect(url_for('main.index'))

    if hoja not in HOJAS:
        flash('La hoja solicitada no existe.', 'danger')
        return _volver(None)

    archivo, armar = HOJAS[hoja]
    try:
        titulo, encabezados, filas, anchos = armar()
        wb = _libro(titulo, encabezados, filas, anchos)
        salida = BytesIO()
        wb.save(salida)
        salida.seek(0)
        wb.close()
    except Exception:
        db.session.rollback()
        current_app.logger.exception('Exportando la hoja "%s"', hoja)
        flash('No se pudo generar el archivo. Intentalo de nuevo.', 'danger')
        return _volver(hoja)

    return send_file(salida, as_attachment=True, download_name=archivo,
                     mimetype=XLSX_MIME)
