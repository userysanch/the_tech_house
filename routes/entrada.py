from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user
from extensions import db
from models import Producto, Entrada, Proveedor, MovimientoInventario
from routes.registros import identificar_producto
from datetime import datetime

entrada_bp = Blueprint('entrada', __name__)


def _redirigir():
    return redirect(url_for('entrada.entrada_view'))


def _id_opcion(campo):
    """Valor entero opcional de un select del formulario."""
    v = (request.form.get(campo) or '').strip()
    try:
        return int(v) if v else None
    except ValueError:
        return None


@entrada_bp.route('/', methods=['GET', 'POST'])
@login_required
def entrada_view():
    if current_user.rol != 'admin':
        flash('Solo el administrador puede registrar compras.', 'danger')
        return redirect(url_for('main.index'))

    if request.method == 'POST':
        # --- eliminar una compra (entrada) ---
        if request.form.get('action') == 'eliminar_entrada':
            id_entrada = request.form.get('id_entrada')
            entrada = Entrada.query.get(id_entrada) if id_entrada else None
            if not entrada:
                flash('La compra indicada no existe.', 'danger')
                return _redirigir()

            codigo_prod = entrada.codigo_producto
            cant = entrada.cantidad

            producto = Producto.query.filter_by(codigo=codigo_prod).first()
            if producto and producto.stock < cant:
                flash(f'No se puede eliminar: "{producto.nombre}" solo tiene '
                      f'{producto.stock} unidades en stock y esta compra fue '
                      f'por {cant}.', 'danger')
                return _redirigir()

            if producto:
                producto.stock -= cant
                stock_final = producto.stock
                nombre_prod = producto.nombre
            else:
                stock_final = None
                nombre_prod = codigo_prod

            # Kardex: la compra eliminada se registra como ajuste negativo
            db.session.add(MovimientoInventario(
                codigo_producto=codigo_prod,
                tipo='ajuste',
                cantidad=-cant,
                referencia=f'Compra #{entrada.id} eliminada',
            ))
            db.session.delete(entrada)
            db.session.commit()

            mensaje = f'Compra de {cant} unidades de "{nombre_prod}" eliminada.'
            if stock_final is not None:
                mensaje += f' Stock en Inventario: {stock_final}.'
            flash(mensaje, 'warning')
            return _redirigir()

        # --- editar una compra (entrada) ---
        if request.form.get('action') == 'editar_entrada':
            id_entrada = request.form.get('id_entrada')
            entrada = Entrada.query.get(id_entrada) if id_entrada else None
            if not entrada:
                flash('La compra indicada no existe.', 'danger')
                return _redirigir()

            fecha_raw = (request.form.get('fecha') or '').strip()
            try:
                nueva_fecha = datetime.strptime(fecha_raw, '%Y-%m-%dT%H:%M')
            except ValueError:
                try:
                    nueva_fecha = datetime.strptime(fecha_raw, '%Y-%m-%dT%H:%M:%S')
                except ValueError:
                    flash('La fecha indicada no es valida.', 'danger')
                    return _redirigir()

            try:
                nueva_cantidad = int(request.form.get('cantidad'))
            except (TypeError, ValueError):
                flash('La cantidad debe ser un numero entero.', 'danger')
                return _redirigir()
            if nueva_cantidad < 1:
                flash('La cantidad debe ser al menos 1.', 'danger')
                return _redirigir()

            try:
                nuevo_costo = float(request.form.get('costo'))
            except (TypeError, ValueError):
                flash('El costo debe ser un numero valido.', 'danger')
                return _redirigir()
            if nuevo_costo <= 0:
                flash('El costo debe ser mayor a cero.', 'danger')
                return _redirigir()

            producto = Producto.query.filter_by(codigo=entrada.codigo_producto).first()
            delta = nueva_cantidad - entrada.cantidad

            if producto and producto.stock + delta < 0:
                flash(f'No se puede: "{producto.nombre}" tiene {producto.stock} en stock '
                      f'y pasar de {entrada.cantidad} a {nueva_cantidad} unidades '
                      f'lo dejaria en {producto.stock + delta}.', 'danger')
                return _redirigir()

            entrada.fecha = nueva_fecha
            entrada.cantidad = nueva_cantidad
            entrada.costo_unitario = nuevo_costo

            if producto:
                producto.stock += delta

            db.session.flush()

            if delta != 0:
                db.session.add(MovimientoInventario(
                    codigo_producto=entrada.codigo_producto,
                    tipo='ajuste',
                    cantidad=delta,
                    referencia=f'Compra #{entrada.id} editada',
                ))

            costo_producto_actualizado = False
            if producto:
                # El costo del producto solo sigue a su compra mas reciente,
                # para no pisar el costo vigente con una compra antigua.
                ultima = (Entrada.query
                          .filter_by(codigo_producto=producto.codigo)
                          .order_by(Entrada.fecha.desc(), Entrada.id.desc())
                          .first())
                if ultima and ultima.id == entrada.id and producto.costo != nuevo_costo:
                    producto.costo = nuevo_costo
                    costo_producto_actualizado = True

            db.session.commit()

            mensaje = (f'Compra actualizada: {nueva_cantidad} unidades a '
                       f'Q{nuevo_costo:.2f}.')
            if producto:
                mensaje += f' Stock en Inventario: {producto.stock}.'
                if costo_producto_actualizado:
                    mensaje += ' Costo del producto actualizado.'
            flash(mensaje, 'success')
            return _redirigir()

        upc = (request.form.get('upc') or '').strip()
        codigo = (request.form.get('codigo') or '').strip()
        nombre = (request.form.get('nombre') or '').strip()

        # --- validaciones basicas ---
        if not upc and not codigo:
            flash('Ingresa el UPC o el Codigo del producto.', 'danger')
            return _redirigir()

        if len(upc) > 50 or len(codigo) > 50:
            flash('El UPC y el Codigo no pueden superar 50 caracteres.', 'danger')
            return _redirigir()

        if len(nombre) > 150:
            flash('El nombre no puede superar 150 caracteres.', 'danger')
            return _redirigir()

        try:
            cantidad = int(request.form.get('cantidad'))
        except (TypeError, ValueError):
            flash('La cantidad debe ser un numero entero.', 'danger')
            return _redirigir()
        if cantidad < 1:
            flash('La cantidad debe ser al menos 1.', 'danger')
            return _redirigir()

        try:
            costo = float(request.form.get('costo'))
        except (TypeError, ValueError):
            flash('El costo debe ser un numero valido.', 'danger')
            return _redirigir()
        if costo <= 0:
            flash('El costo debe ser mayor a cero.', 'danger')
            return _redirigir()

        # --- margen y precio de venta (misma logica que Inventario) ---
        margen_raw = (request.form.get('margen') or '').strip()
        precio_raw = (request.form.get('precio') or '').strip()

        try:
            margen_val = float(margen_raw) if margen_raw != '' else None
            precio_val = float(precio_raw) if precio_raw != '' else None
        except ValueError:
            flash('El margen y el precio deben ser numeros validos.', 'danger')
            return _redirigir()

        if margen_val is not None and precio_val is not None:
            precio_val = round(costo * (1 + margen_val / 100), 2)
        elif precio_val is not None:
            margen_val = round(((precio_val / costo) - 1) * 100, 2)
        elif margen_val is not None:
            precio_val = round(costo * (1 + margen_val / 100), 2)
        # ambos vacios: no tocar el precio del producto (si es nuevo, se usan los defaults)

        if precio_val is not None and precio_val <= 0:
            flash('El precio de venta debe ser mayor a cero.', 'danger')
            return _redirigir()

        # --- identificar el producto en la matriz (Registros Nuevos) ---
        producto, conflicto = identificar_producto(upc, codigo)
        if conflicto:
            flash(conflicto, 'danger')
            return _redirigir()

        if not producto:
            # UPC no coincide y no se indico un codigo existente
            if upc and not codigo:
                flash(f'No existe ningun producto con UPC "{upc}". '
                      f'Ingresa el Codigo para crearlo.', 'danger')
                return _redirigir()

            if not nombre:
                flash('El producto no existe. Debes ingresar un Nombre para crearlo.',
                      'warning')
                return _redirigir()

            producto = Producto(
                codigo=codigo,
                nombre=nombre,
                costo=costo,
                margen=0,
                precio=costo,
                stock=0,
                codigo_barras=upc if upc and upc != codigo else None,
            )
            db.session.add(producto)
            db.session.flush()
        else:
            # El producto existe: completar su barcode si no lo tiene
            if upc and upc != producto.codigo:
                if producto.codigo_barras is None:
                    producto.codigo_barras = upc
                elif producto.codigo_barras != upc:
                    flash(f'El producto {producto.codigo} ya tiene el UPC '
                          f'"{producto.codigo_barras}" y no coincide con "{upc}".', 'danger')
                    return _redirigir()

        nueva_entrada = Entrada(
            fecha=datetime.utcnow(),
            codigo_producto=producto.codigo,
            cantidad=cantidad,
            costo_unitario=costo,
            upc=producto.codigo_barras,
            proveedor_id=_id_opcion('proveedor_id'),
        )
        db.session.add(nueva_entrada)
        db.session.flush()

        # Kardex de inventario: la compra siempre deja trazabilidad
        db.session.add(MovimientoInventario(
            codigo_producto=producto.codigo,
            tipo='entrada',
            cantidad=cantidad,
            referencia=f'Compra #{nueva_entrada.id}',
        ))

        producto.stock += cantidad
        producto.costo = costo

        if margen_val is not None:
            producto.margen = margen_val
            producto.precio = precio_val

        db.session.commit()

        mensaje = (f'Compra de {cantidad} unidades de "{producto.nombre}" '
                   f'registrada con exito.')
        if margen_val is not None:
            mensaje += (f' Precio de venta Q{precio_val:.2f} '
                        f'(margen {margen_val:.2f}%).')
        flash(mensaje, 'success')
        return _redirigir()

    entradas_recientes = Entrada.query.order_by(Entrada.fecha.desc()).all()
    proveedores = Proveedor.query.order_by(Proveedor.nombre).all()
    return render_template('entrada.html', entradas=entradas_recientes,
                           proveedores=proveedores)
