from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user
from sqlalchemy.exc import IntegrityError
from extensions import db
from models import Categoria, Marca, Proveedor, Cliente, FormaPago, Role

catalogos_bp = Blueprint('catalogos', __name__)

# Configuracion generica de los catalogos manejables desde una sola pantalla.
TIPOS = {
    'categorias': {
        'titulo': 'Categorias', 'icono': 'ti-tag',
        'modelo': Categoria, 'unico_nombre': True,
        'campos': [
            ('nombre', 'Nombre', True, 80),
            ('descripcion', 'Descripcion', False, 200),
        ],
        'ayuda': 'Las categorias agrupan los productos y alimentan los reportes de ventas por categoria.',
    },
    'marcas': {
        'titulo': 'Marcas', 'icono': 'ti-bookmark',
        'modelo': Marca, 'unico_nombre': True,
        'campos': [('nombre', 'Nombre', True, 80)],
        'ayuda': 'Marcas de los productos del inventario.',
    },
    'proveedores': {
        'titulo': 'Proveedores', 'icono': 'ti-truck-delivery',
        'modelo': Proveedor, 'unico_nombre': False,
        'campos': [
            ('nombre', 'Nombre', True, 150),
            ('nit', 'NIT', False, 30),
            ('telefono', 'Telefono', False, 30),
            ('email', 'Email', False, 100),
            ('direccion', 'Direccion', False, 200),
        ],
        'ayuda': 'Se selecciona al registrar una compra (Entrada de mercancia).',
    },
    'clientes': {
        'titulo': 'Clientes', 'icono': 'ti-users',
        'modelo': Cliente, 'unico_nombre': False,
        'campos': [
            ('nombre', 'Nombre', True, 150),
            ('nit', 'NIT', False, 30),
            ('telefono', 'Telefono', False, 30),
            ('email', 'Email', False, 100),
            ('direccion', 'Direccion', False, 200),
        ],
        'ayuda': 'Se selecciona al cobrar en Caja y queda ligado a la venta.',
    },
    'formas_pago': {
        'titulo': 'Formas de pago', 'icono': 'ti-credit-card',
        'modelo': FormaPago, 'unico_nombre': True,
        'campos': [('nombre', 'Nombre', True, 50)],
        'ayuda': 'Botones disponibles al cobrar en Caja (Efectivo, Tarjeta, Transferencia).',
    },
    'roles': {
        'titulo': 'Roles', 'icono': 'ti-shield-check',
        'modelo': Role, 'unico_nombre': True,
        'campos': [
            ('nombre', 'Nombre', True, 30),
            ('descripcion', 'Descripcion', False, 150),
        ],
        'ayuda': 'Roles asignados a los usuarios desde la pantalla Usuarios.',
    },
}


def _admin():
    if current_user.rol != 'admin':
        flash('Solo el administrador puede gestionar catalogos.', 'danger')
        return redirect(url_for('main.index'))
    return None


def _valor(campo, maxlen):
    v = (request.form.get(campo) or '').strip()
    if len(v) > maxlen:
        flash(f'El campo "{campo}" no puede superar {maxlen} caracteres.', 'danger')
        return None
    return v


@catalogos_bp.route('/<tipo>', methods=['GET', 'POST'])
@login_required
def catalogo_view(tipo):
    deny = _admin()
    if deny:
        return deny

    cfg = TIPOS.get(tipo)
    if not cfg:
        flash('Catalogo inexistente.', 'danger')
        return redirect(url_for('catalogos.catalogo_view', tipo='categorias'))

    modelo = cfg['modelo']

    if request.method == 'POST':
        action = request.form.get('action')

        # ---- ELIMINAR ----
        if action == 'eliminar':
            id_fila = (request.form.get('id') or '').strip()
            try:
                fila = db.session.get(modelo, int(id_fila)) if id_fila else None
            except ValueError:
                fila = None
            if not fila:
                flash('El registro indicado no existe.', 'danger')
                return redirect(url_for('catalogos.catalogo_view', tipo=tipo))
            nombre = getattr(fila, 'nombre', f'#{id_fila}')
            try:
                db.session.delete(fila)
                db.session.commit()
                flash(f'Registro "{nombre}" eliminado.', 'warning')
            except IntegrityError:
                db.session.rollback()
                flash(f'No se puede eliminar "{nombre}": esta en uso por otras tablas '
                      f'(productos, usuarios o ventas).', 'danger')
            except Exception:
                db.session.rollback()
                flash('No se pudo eliminar el registro.', 'danger')
            return redirect(url_for('catalogos.catalogo_view', tipo=tipo))

        # ---- CREAR / EDITAR ----
        id_fila = (request.form.get('id') or '').strip()
        if id_fila:
            try:
                id_fila = int(id_fila)
            except ValueError:
                id_fila = None
        valores = {}
        valido = True
        for nombre_campo, etiqueta, requerido, maxlen in cfg['campos']:
            v = _valor(nombre_campo, maxlen)
            if v is None:
                valido = False
                break
            if requerido and not v:
                flash(f'"{etiqueta}" es obligatorio.', 'danger')
                valido = False
                break
            valores[nombre_campo] = v if v != '' else None
        if not valido:
            return redirect(url_for('catalogos.catalogo_view', tipo=tipo))

        # Unicidad del nombre en catalogos con nombre unico
        if cfg['unico_nombre'] and valores.get('nombre'):
            q = modelo.query.filter_by(nombre=valores['nombre'])
            if id_fila:
                q = q.filter(modelo.id != id_fila)
            if q.first():
                flash(f'Ya existe un registro con el nombre "{valores["nombre"]}".', 'danger')
                return redirect(url_for('catalogos.catalogo_view', tipo=tipo))

        try:
            if id_fila:
                fila = db.session.get(modelo, id_fila)
                if not fila:
                    flash('El registro indicado no existe.', 'danger')
                    return redirect(url_for('catalogos.catalogo_view', tipo=tipo))
                for campo, valor in valores.items():
                    setattr(fila, campo, valor)
                db.session.commit()
                flash(f'"{valores.get("nombre") or "Registro"}" actualizado correctamente.', 'success')
            else:
                fila = modelo(**valores)
                db.session.add(fila)
                db.session.commit()
                flash(f'"{valores.get("nombre") or "Registro"}" creado correctamente.', 'success')
        except IntegrityError:
            db.session.rollback()
            flash('Ese valor ya esta registrado (clave duplicada).', 'danger')
        except Exception:
            db.session.rollback()
            flash('No se pudo guardar el registro.', 'danger')
        return redirect(url_for('catalogos.catalogo_view', tipo=tipo))

    filas = modelo.query.order_by(modelo.nombre).all() if hasattr(modelo, 'nombre') \
        else modelo.query.order_by(modelo.id).all()
    return render_template('catalogos.html', tipo=tipo, cfg=cfg, filas=filas, tipos=TIPOS)
