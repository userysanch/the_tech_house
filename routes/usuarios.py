from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user
from sqlalchemy.exc import IntegrityError
from extensions import db
from models import Usuario, Role

usuarios_bp = Blueprint('usuarios', __name__)


def _admin():
    if current_user.rol != 'admin':
        flash('Solo el administrador gestiona los usuarios.', 'danger')
        return redirect(url_for('main.index'))
    return None


@usuarios_bp.route('/', methods=['GET', 'POST'])
@login_required
def usuarios_view():
    deny = _admin()
    if deny:
        return deny

    if request.method == 'POST':
        action = request.form.get('action')

        # ---- CREAR ----
        if action == 'crear':
            username = (request.form.get('username') or '').strip().lower()
            nombre = (request.form.get('nombre') or '').strip()
            password = request.form.get('password') or ''
            rol_id = (request.form.get('rol_id') or '').strip()

            if not username or not nombre:
                flash('Usuario y nombre son obligatorios.', 'danger')
                return redirect(url_for('usuarios.usuarios_view'))
            if len(username) > 80 or len(nombre) > 150:
                flash('Usuario maximo 80 caracteres y nombre 150.', 'danger')
                return redirect(url_for('usuarios.usuarios_view'))
            if len(password) < 6:
                flash('La contrasena debe tener al menos 6 caracteres.', 'danger')
                return redirect(url_for('usuarios.usuarios_view'))
            if Usuario.query.filter_by(username=username).first():
                flash(f'El usuario "{username}" ya existe.', 'danger')
                return redirect(url_for('usuarios.usuarios_view'))

            rol = db.session.get(Role, int(rol_id)) if rol_id.isdigit() else None
            if not rol:
                flash('Selecciona un rol valido (tabla roles).', 'danger')
                return redirect(url_for('usuarios.usuarios_view'))

            u = Usuario(username=username, nombre=nombre,
                        rol='admin' if rol.nombre == 'admin' else 'empleado',
                        rol_id=rol.id)
            u.set_password(password)
            db.session.add(u)
            db.session.commit()
            flash(f'Usuario "{username}" creado con rol {rol.nombre}.', 'success')
            return redirect(url_for('usuarios.usuarios_view'))

        # ---- EDITAR ----
        if action == 'editar':
            id_user = (request.form.get('id') or '').strip()
            try:
                u = db.session.get(Usuario, int(id_user))
            except ValueError:
                u = None
            if not u:
                flash('El usuario indicado no existe.', 'danger')
                return redirect(url_for('usuarios.usuarios_view'))

            nombre = (request.form.get('nombre') or '').strip()
            password = request.form.get('password') or ''
            rol_id = (request.form.get('rol_id') or '').strip()

            if not nombre:
                flash('El nombre es obligatorio.', 'danger')
                return redirect(url_for('usuarios.usuarios_view'))

            rol = db.session.get(Role, int(rol_id)) if rol_id.isdigit() else None
            if not rol:
                flash('Selecciona un rol valido.', 'danger')
                return redirect(url_for('usuarios.usuarios_view'))

            if password and len(password) < 6:
                flash('La contrasena nueva debe tener al menos 6 caracteres.', 'danger')
                return redirect(url_for('usuarios.usuarios_view'))

            u.nombre = nombre
            u.rol = 'admin' if rol.nombre == 'admin' else 'empleado'
            u.rol_id = rol.id
            if password:
                u.set_password(password)
            db.session.commit()
            flash(f'Usuario "{u.username}" actualizado.', 'success')
            return redirect(url_for('usuarios.usuarios_view'))

        # ---- ELIMINAR ----
        if action == 'eliminar':
            id_user = (request.form.get('id') or '').strip()
            try:
                u = db.session.get(Usuario, int(id_user))
            except ValueError:
                u = None
            if not u:
                flash('El usuario indicado no existe.', 'danger')
                return redirect(url_for('usuarios.usuarios_view'))
            if u.id == current_user.id:
                flash('No puedes eliminar tu propia cuenta.', 'danger')
                return redirect(url_for('usuarios.usuarios_view'))
            try:
                db.session.delete(u)
                db.session.commit()
                flash(f'Usuario "{u.username}" eliminado.', 'warning')
            except IntegrityError:
                db.session.rollback()
                flash('No se puede eliminar: el usuario tiene turnos de caja '
                      'asociados (foreign key en turnos_caja).', 'danger')
            except Exception:
                db.session.rollback()
                flash('No se pudo eliminar el usuario.', 'danger')
            return redirect(url_for('usuarios.usuarios_view'))

    usuarios = Usuario.query.order_by(Usuario.id).all()
    roles = Role.query.order_by(Role.id).all()
    return render_template('usuarios.html', usuarios=usuarios, roles=roles)
