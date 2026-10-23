from functools import wraps

from flask import (Blueprint, current_app, flash, redirect, render_template,
                   request, url_for)
from flask_login import login_required, current_user
from sqlalchemy import or_
from extensions import db
from models import Producto, Entrada, DetalleVenta

inventario_bp = Blueprint('inventario', __name__)

# Topes de las columnas de MySQL (productos).
LIM_IMPORTE = 99999999.99    # costo / precio -> decimal(10,2)
LIM_MARGEN = 99999999.99     # margen         -> decimal(9,2)


def _sin_500(vista):
    """No deja que una excepcion se convierta en la consola de depuracion
    (83 KB de HTML) que ngrok no logra entregar y se vuelve ERR_NGROK_3004."""
    @wraps(vista)
    def _wrapper(*args, **kwargs):
        try:
            return vista(*args, **kwargs)
        except Exception:
            db.session.rollback()
            current_app.logger.exception('Error en %s %s',
                                         request.method, request.path)
            if request.method != 'POST':
                raise
            flash('Ocurrio un error inesperado y NO se guardo ningun cambio. '
                  'Revisa los datos e intentalo de nuevo.', 'danger')
            return redirect(url_for('inventario.inventario_view'))
    return _wrapper


def _volver():
    return redirect(url_for('inventario.inventario_view'))


def _existe_codigo(codigo, excluir_id=None):
    q = Producto.query.filter_by(codigo=codigo)
    if excluir_id is not None:
        q = q.filter(Producto.id != excluir_id)
    return q.first() is not None


@inventario_bp.route('/', methods=['GET', 'POST'])
@login_required
@_sin_500
def inventario_view():
    if current_user.rol != 'admin':
        flash('No tienes acceso a inventario.', 'danger')
        return redirect(url_for('main.index'))

    if request.method == 'POST':
        action = request.form.get('action')

        # ---- GUARDAR (crear o editar) ----
        if action == 'guardar':
            id_prod = (request.form.get('id_producto') or '').strip()
            codigo = request.form.get('codigo', '').strip()
            nombre = request.form.get('nombre', '').strip()
            upc = request.form.get('upc', '').strip()
            costo_raw = request.form.get('costo', '').strip()
            margen = request.form.get('margen', '').strip()
            precio = request.form.get('precio', '').strip()

            if not codigo or not nombre:
                flash('Codigo y nombre son obligatorios.', 'danger')
                return _volver()

            if len(codigo) > 50 or len(nombre) > 150 or len(upc) > 50:
                flash('El codigo y el UPC no pueden superar 50 caracteres, '
                      'ni el nombre 150.', 'danger')
                return _volver()

            try:
                costo = float(costo_raw) if costo_raw else 0.0
            except ValueError:
                costo = -1.0

            if costo <= 0:
                flash('El costo debe ser mayor a cero.', 'danger')
                return _volver()

            try:
                margen_val = float(margen) if margen != '' else None
                precio_val = float(precio) if precio != '' else None
            except ValueError:
                flash('El margen y el precio deben ser numeros validos.', 'danger')
                return _volver()

            # El precio siempre se deriva del costo + margen (la hoja de texto
            # del formulario dice: cambia el margen y se calcula el precio, o
            # escribe el precio y se calcula el margen).
            if margen_val is not None and precio_val is not None:
                precio_val = round(costo * (1 + margen_val / 100), 2)
            elif precio_val is not None and margen_val is None:
                margen_val = round(((precio_val / costo) - 1) * 100, 2)
            elif margen_val is not None and precio_val is None:
                precio_val = round(costo * (1 + margen_val / 100), 2)
            else:
                margen_val = 0.0
                precio_val = costo

            # Topes de las columnas. Sin esto MySQL lanza 1264 "Out of range"
            # y la pagina se cae en vez de avisar al usuario.
            if abs(margen_val) > LIM_MARGEN:
                flash(f'El margen calculado ({margen_val:,.2f}%) supera el maximo '
                      f'permitido ({LIM_MARGEN:,.2f}%). Ajusta el costo o el precio.',
                      'danger')
                return _volver()

            if precio_val < 0 or costo > LIM_IMPORTE or precio_val > LIM_IMPORTE:
                flash('El costo y el precio deben estar entre Q0.00 y Q99,999,999.99.',
                      'danger')
                return _volver()

            # ---- EDITAR ----
            if id_prod:
                producto = Producto.query.get(id_prod)
                if not producto:
                    flash('El producto a editar no existe.', 'danger')
                    return _volver()

                if _existe_codigo(codigo, excluir_id=producto.id):
                    flash('El codigo ya existe.', 'danger')
                    return _volver()

                codigo_anterior = producto.codigo
                producto.codigo = codigo
                producto.nombre = nombre
                producto.codigo_barras = upc if upc else None
                producto.costo = round(costo, 2)
                producto.margen = round(margen_val, 2)
                producto.precio = round(precio_val, 2)

                # El FK de entradas propaga solo (ON UPDATE CASCADE),
                # pero detalle_ventas no tiene FK: se actualiza a mano.
                if codigo_anterior != codigo:
                    DetalleVenta.query.filter_by(
                        codigo_producto=codigo_anterior
                    ).update({'codigo_producto': codigo}, synchronize_session=False)

                db.session.commit()
                flash(f'Producto "{codigo}" actualizado correctamente.', 'success')
                return _volver()

            # ---- CREAR ----
            if _existe_codigo(codigo):
                flash('El codigo ya existe.', 'danger')
                return _volver()

            nuevo = Producto(
                codigo=codigo,
                nombre=nombre,
                codigo_barras=upc if upc else None,
                costo=round(costo, 2),
                margen=round(margen_val, 2),
                precio=round(precio_val, 2),
                stock=0,
            )
            db.session.add(nuevo)
            db.session.commit()
            flash('Producto creado correctamente.', 'success')
            return _volver()

        # ---- ELIMINAR ----
        if action == 'eliminar':
            id_prod = (request.form.get('id_producto') or '').strip()
            producto = Producto.query.get(id_prod) if id_prod else None
            if not producto:
                flash('El producto a eliminar no existe.', 'danger')
                return _volver()

            n_ent = Entrada.query.filter_by(codigo_producto=producto.codigo).count()
            n_det = DetalleVenta.query.filter_by(codigo_producto=producto.codigo).count()
            if n_ent or n_det:
                mensaje = (f'No se puede eliminar "{producto.codigo}": tiene '
                           f'{n_ent} compra(s) y {n_det} venta(s) registradas.')
                if n_det:
                    mensaje += ' Anula primero la venta desde Ventas.'
                if n_ent:
                    mensaje += ' Borra la compra desde Compras.'
                flash(mensaje, 'danger')
                return _volver()

            codigo_borrado = producto.codigo
            db.session.delete(producto)
            db.session.commit()
            flash(f'Producto "{codigo_borrado}" eliminado.', 'warning')
            return _volver()

        return _volver()

    # Inventario solo lista lo que tiene existencias o alguna compra
    # registrada. El catalogo completo (los 145) vive en Registros Nuevos.
    productos = (Producto.query
                 .outerjoin(Entrada, Entrada.codigo_producto == Producto.codigo)
                 .filter(or_(Producto.stock > 0, Entrada.id.isnot(None)))
                 .distinct()
                 .order_by(Producto.id.asc())
                 .all())
    return render_template('inventario.html', productos=productos)
