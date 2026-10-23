from extensions import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime


# ============================================================
# Catalogos
# ============================================================

class Role(db.Model):
    __tablename__ = 'roles'

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(30), unique=True, nullable=False)
    descripcion = db.Column(db.String(150), nullable=False, default='')

    usuarios = db.relationship('Usuario', backref='rol_tipo', lazy=True)


class Categoria(db.Model):
    __tablename__ = 'categorias'

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(80), unique=True, nullable=False)
    descripcion = db.Column(db.String(200), nullable=False, default='')

    productos = db.relationship('Producto', backref='categoria', lazy=True)


class Marca(db.Model):
    __tablename__ = 'marcas'

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(80), unique=True, nullable=False)

    productos = db.relationship('Producto', backref='marca', lazy=True)


class Proveedor(db.Model):
    __tablename__ = 'proveedores'

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(150), nullable=False)
    nit = db.Column(db.String(30), unique=True, nullable=True)
    telefono = db.Column(db.String(30), nullable=True)
    email = db.Column(db.String(100), nullable=True)
    direccion = db.Column(db.String(200), nullable=True)

    productos = db.relationship('Producto', backref='proveedor', lazy=True)
    entradas = db.relationship('Entrada', backref='proveedor', lazy=True)


class Cliente(db.Model):
    __tablename__ = 'clientes'

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(150), nullable=False)
    nit = db.Column(db.String(30), unique=True, nullable=True)
    telefono = db.Column(db.String(30), nullable=True)
    email = db.Column(db.String(100), nullable=True)
    direccion = db.Column(db.String(200), nullable=True)

    ventas = db.relationship('Venta', backref='cliente', lazy=True)


class FormaPago(db.Model):
    __tablename__ = 'formas_pago'

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(50), unique=True, nullable=False)

    pagos = db.relationship('PagoVenta', backref='forma', lazy=True)


# ============================================================
# Usuarios e inventario
# ============================================================

class Usuario(UserMixin, db.Model):
    __tablename__ = 'usuarios'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    nombre = db.Column(db.String(150), nullable=False)
    rol = db.Column(db.String(20), nullable=False, default='empleado')
    rol_id = db.Column(db.Integer, db.ForeignKey('roles.id'), nullable=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<Usuario {self.username}>'


class Producto(db.Model):
    __tablename__ = 'productos'

    id = db.Column(db.Integer, primary_key=True)
    codigo = db.Column(db.String(50), unique=True, nullable=False)
    nombre = db.Column(db.String(150), nullable=False)
    costo = db.Column(db.Numeric(10, 2), nullable=False, default=0.00)
    margen = db.Column(db.Numeric(5, 2), nullable=False, default=0.00)
    precio = db.Column(db.Numeric(10, 2), nullable=False, default=0.00)
    stock = db.Column(db.Integer, nullable=False, default=0)
    codigo_barras = db.Column(db.String(50), nullable=True, default=None)
    categoria_id = db.Column(db.Integer, db.ForeignKey('categorias.id'), nullable=True)
    marca_id = db.Column(db.Integer, db.ForeignKey('marcas.id'), nullable=True)
    proveedor_id = db.Column(db.Integer, db.ForeignKey('proveedores.id'), nullable=True)

    entradas = db.relationship('Entrada', backref='producto', lazy=True)
    detalles = db.relationship('DetalleVenta', backref='producto', lazy=True)
    movimientos = db.relationship('MovimientoInventario', backref='producto', lazy=True)
    promociones = db.relationship('Promocion', backref='producto', lazy=True)


class Entrada(db.Model):
    __tablename__ = 'entradas'

    id = db.Column(db.Integer, primary_key=True)
    fecha = db.Column(db.DateTime, default=datetime.utcnow)
    codigo_producto = db.Column(db.String(50), db.ForeignKey('productos.codigo'), nullable=False)
    cantidad = db.Column(db.Integer, nullable=False)
    costo_unitario = db.Column(db.Numeric(10, 2), nullable=False)
    upc = db.Column(db.String(50), nullable=True, default=None)
    proveedor_id = db.Column(db.Integer, db.ForeignKey('proveedores.id'), nullable=True)


class MovimientoInventario(db.Model):
    __tablename__ = 'movimientos_inventario'

    id = db.Column(db.Integer, primary_key=True)
    codigo_producto = db.Column(db.String(50), db.ForeignKey('productos.codigo'), nullable=False)
    tipo = db.Column(db.Enum('entrada', 'salida', 'ajuste', 'devolucion', name='tipo_movimiento'),
                     nullable=False)
    cantidad = db.Column(db.Integer, nullable=False)
    fecha = db.Column(db.DateTime, default=datetime.utcnow)
    referencia = db.Column(db.String(150), nullable=False, default='')


class Promocion(db.Model):
    __tablename__ = 'promociones'

    id = db.Column(db.Integer, primary_key=True)
    codigo_producto = db.Column(db.String(50), db.ForeignKey('productos.codigo'), nullable=False)
    descripcion = db.Column(db.String(150), nullable=False)
    porcentaje = db.Column(db.Numeric(5, 2), nullable=False, default=0.00)
    fecha_inicio = db.Column(db.DateTime, nullable=False)
    fecha_fin = db.Column(db.DateTime, nullable=False)
    activa = db.Column(db.Boolean, nullable=False, default=True)


# ============================================================
# Ventas y cobros
# ============================================================

class Venta(db.Model):
    __tablename__ = 'ventas'

    id = db.Column(db.Integer, primary_key=True)
    fecha = db.Column(db.DateTime, default=datetime.utcnow)
    total_venta = db.Column(db.Numeric(10, 2), nullable=False, default=0.00)
    ganancia_total = db.Column(db.Numeric(10, 2), nullable=False, default=0.00)
    cliente_id = db.Column(db.Integer, db.ForeignKey('clientes.id'), nullable=True)

    detalles = db.relationship('DetalleVenta', backref='venta', lazy=True)
    pagos = db.relationship('PagoVenta', backref='venta', lazy=True)
    devoluciones = db.relationship('Devolucion', backref='venta', lazy=True)


class DetalleVenta(db.Model):
    __tablename__ = 'detalle_ventas'

    id = db.Column(db.Integer, primary_key=True)
    venta_id = db.Column(db.Integer, db.ForeignKey('ventas.id'), nullable=False)
    codigo_producto = db.Column(db.String(50), db.ForeignKey('productos.codigo'), nullable=False)
    cantidad = db.Column(db.Integer, nullable=False)
    precio_unitario = db.Column(db.Numeric(10, 2), nullable=False)
    total = db.Column(db.Numeric(10, 2), nullable=False)
    ganancia = db.Column(db.Numeric(10, 2), nullable=False, default=0.00)


class PagoVenta(db.Model):
    __tablename__ = 'pagos_venta'

    id = db.Column(db.Integer, primary_key=True)
    venta_id = db.Column(db.Integer, db.ForeignKey('ventas.id'), nullable=False)
    forma_pago_id = db.Column(db.Integer, db.ForeignKey('formas_pago.id'), nullable=False)
    monto = db.Column(db.Numeric(10, 2), nullable=False)
    fecha = db.Column(db.DateTime, default=datetime.utcnow)


class Devolucion(db.Model):
    __tablename__ = 'devoluciones'

    id = db.Column(db.Integer, primary_key=True)
    venta_id = db.Column(db.Integer, db.ForeignKey('ventas.id'), nullable=False)
    fecha = db.Column(db.DateTime, default=datetime.utcnow)
    motivo = db.Column(db.String(200), nullable=False, default='')
    monto_total = db.Column(db.Numeric(10, 2), nullable=False, default=0.00)

    detalles = db.relationship('DetalleDevolucion', backref='devolucion', lazy=True)


class DetalleDevolucion(db.Model):
    __tablename__ = 'detalle_devoluciones'

    id = db.Column(db.Integer, primary_key=True)
    devolucion_id = db.Column(db.Integer, db.ForeignKey('devoluciones.id'), nullable=False)
    codigo_producto = db.Column(db.String(50), db.ForeignKey('productos.codigo'), nullable=False)
    cantidad = db.Column(db.Integer, nullable=False)
    subtotal = db.Column(db.Numeric(10, 2), nullable=False, default=0.00)


class VentaPendiente(db.Model):
    __tablename__ = 'ventas_pendientes'

    id = db.Column(db.Integer, primary_key=True)
    scanner_code = db.Column(db.String(50), nullable=False)
    producto_codigo = db.Column(db.String(50), nullable=False)
    producto_nombre = db.Column(db.String(150), nullable=False)
    cantidad = db.Column(db.Integer, nullable=False, default=1)
    precio_unitario = db.Column(db.Numeric(10, 2), nullable=False)
    total = db.Column(db.Numeric(10, 2), nullable=False)
    celular_ip = db.Column(db.String(50), nullable=True)
    fecha = db.Column(db.DateTime, default=datetime.utcnow)
    estado = db.Column(db.String(20), nullable=False, default='pendiente')


# ============================================================
# Caja
# ============================================================

class Caja(db.Model):
    __tablename__ = 'cajas'

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(60), unique=True, nullable=False)
    ubicacion = db.Column(db.String(120), nullable=False, default='')

    turnos = db.relationship('TurnoCaja', backref='caja', lazy=True)


class TurnoCaja(db.Model):
    __tablename__ = 'turnos_caja'

    id = db.Column(db.Integer, primary_key=True)
    caja_id = db.Column(db.Integer, db.ForeignKey('cajas.id'), nullable=False)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    fecha_apertura = db.Column(db.DateTime, default=datetime.utcnow)
    fecha_cierre = db.Column(db.DateTime, nullable=True)
    saldo_inicial = db.Column(db.Numeric(10, 2), nullable=False, default=0.00)
    saldo_final = db.Column(db.Numeric(10, 2), nullable=True)
    estado = db.Column(db.Enum('abierto', 'cerrado', name='estado_turno'),
                       nullable=False, default='abierto')

    movimientos = db.relationship('MovimientoCaja', backref='turno', lazy=True)


class MovimientoCaja(db.Model):
    __tablename__ = 'movimientos_caja'

    id = db.Column(db.Integer, primary_key=True)
    turno_id = db.Column(db.Integer, db.ForeignKey('turnos_caja.id'), nullable=False)
    tipo = db.Column(db.Enum('ingreso', 'egreso', 'venta', name='tipo_movimiento_caja'),
                     nullable=False)
    monto = db.Column(db.Numeric(10, 2), nullable=False)
    descripcion = db.Column(db.String(150), nullable=False, default='')
    fecha = db.Column(db.DateTime, default=datetime.utcnow)
