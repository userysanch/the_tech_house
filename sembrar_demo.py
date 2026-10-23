# -*- coding: utf-8 -*-
"""
Semilla de datos de demostracion para The Tech House.

Crea (solo si la base esta vacia):
  - 2 proveedores y 2 clientes
  - 6 productos con categoria/marca/proveedor (entradas con kardex)
  - 3 ventas (2 de este mes, 1 del mes pasado) con pagos y kardex
  - 1 devolucion (repon stock + kardex)
  - 1 turno de caja cerrado con movimientos
  - 1 promocion activa (visible con descuento en Caja)

Uso:  python sembrar_demo.py
Para borrar todo lo demo:  mysql -u root -p < limpiar_demo.sql
"""
import sys, os
from datetime import datetime, timedelta

PROY = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROY)
os.chdir(PROY)

from app import create_app
from extensions import db
from models import (
    Categoria, Marca, FormaPago, Usuario, Caja, Proveedor, Cliente,
    Producto, Entrada, MovimientoInventario, Venta, DetalleVenta,
    PagoVenta, Devolucion, DetalleDevolucion, TurnoCaja, MovimientoCaja,
    Promocion,
)

app = create_app()


def q(valor):
    return round(float(valor), 2)


with app.app_context():
    if Producto.query.count() > 0:
        print('La base ya tiene datos; no se siembra de nuevo.')
        sys.exit(0)

    ahora = datetime.utcnow()
    primero_mes = datetime(ahora.year, ahora.month, 1)
    fecha_mes_pasado = primero_mes - timedelta(days=2)

    # ---- Catalogos propios de la demo ----
    prov1 = Proveedor(nombre='Distribuidora Tech GT', nit='1234567-9',
                      telefono='2233-4455', email='ventas@techgt.gt',
                      direccion='Zona 10, Guatemala')
    prov2 = Proveedor(nombre='Importaciones Byte S.A.', nit='9876543-2',
                      telefono='2344-8899', email='contacto@byte.com.gt',
                      direccion='Zone 4, Guatemala')
    cli1 = Cliente(nombre='Carlos Mendez', nit='8541236-7',
                   telefono='5511-2233', email='carlos@email.com')
    cli2 = Cliente(nombre='Soluciones Empresariales GT', nit='4455667-1',
                   telefono='2277-0099', email='compras@solgt.gt',
                   direccion='Torre Citica, suite 901')
    db.session.add_all([prov1, prov2, cli1, cli2])
    db.session.flush()

    cats = {c.nombre: c.id for c in Categoria.query.all()}
    marcas = {m.nombre: m.id for m in Marca.query.all()}
    admin = Usuario.query.filter_by(username='admin').first()
    caja = Caja.query.order_by(Caja.id).first()
    fp_efectivo = FormaPago.query.filter_by(nombre='Efectivo').first()
    fp_tarjeta = FormaPago.query.filter_by(nombre='Tarjeta').first()
    fp_transf = FormaPago.query.filter_by(nombre='Transferencia').first()

    # ---- Productos: (codigo, nombre, costo, margen, stock_final, cat, marca, prov) ----
    defs = [
        ('P001', 'Mouse Genius DX-110', 45.00, 40, 15, 'Accesorios', 'Genius', prov1),
        ('P002', 'Teclado Logitech K120', 95.00, 35, 12, 'Accesorios', 'Logitech', prov1),
        ('P003', 'Audifonos Genius HS-400', 120.00, 45, 10, 'Accesorios', 'Genius', prov2),
        ('P004', 'SSD Kingston 480GB', 380.00, 30, 6, 'Electronica', 'Generico', prov2),
        ('P005', 'Cable HDMI 2m', 25.00, 60, 26, 'General', 'Generico', prov1),
        ('P006', 'Antivirus 1 ano (digital)', 200.00, 50, 20, 'Software', 'Generico', prov2),
    ]
    # unidades vendidas planificadas (para calcular las entradas)
    vendidas = {'P001': 2, 'P002': 3, 'P003': 1, 'P004': 1, 'P005': 3, 'P006': 0}
    # P005: ademas se devuelve 1 unidad en la devolucion

    productos = {}
    for codigo, nombre, costo, margen, stock, cat, marca, prov in defs:
        precio = q(costo * (1 + margen / 100))
        p = Producto(codigo=codigo, nombre=nombre, costo=q(costo),
                     margen=margen, precio=precio, stock=stock,
                     categoria_id=cats[cat], marca_id=marcas[marca],
                     proveedor_id=prov.id)
        db.session.add(p)
        productos[codigo] = p
    db.session.flush()

    # ---- Entradas (compras) + kardex ----
    fecha_compra = ahora - timedelta(days=25)
    for codigo, p in productos.items():
        cantidad = p.stock + vendidas[codigo]
        e = Entrada(fecha=fecha_compra, codigo_producto=codigo,
                    cantidad=cantidad, costo_unitario=p.costo,
                    upc=p.codigo_barras, proveedor_id=p.proveedor_id)
        db.session.add(e)
        db.session.flush()
        db.session.add(MovimientoInventario(
            codigo_producto=codigo, tipo='entrada', cantidad=cantidad,
            fecha=fecha_compra, referencia=f'Compra #{e.id} (demo)'))

    # ---- Ventas ----
    formas = {p.id: p for p in [fp_efectivo, fp_tarjeta, fp_transf]}

    def crear_venta(fecha, items, cliente, forma, forma_id):
        """items = [(codigo, cantidad)] a precio de lista."""
        v = Venta(fecha=fecha, total_venta=0, ganancia_total=0,
                  cliente_id=cliente.id if cliente else None)
        db.session.add(v)
        db.session.flush()
        total = ganancia = 0.0
        for codigo, cantidad in items:
            p = productos[codigo]
            sub = q(p.precio * cantidad)
            gan = q((p.precio - p.costo) * cantidad)
            db.session.add(DetalleVenta(
                venta_id=v.id, codigo_producto=codigo, cantidad=cantidad,
                precio_unitario=p.precio, total=sub, ganancia=gan))
            p.stock -= cantidad
            total += sub
            ganancia += gan
            db.session.add(MovimientoInventario(
                codigo_producto=codigo, tipo='salida', cantidad=cantidad,
                fecha=fecha, referencia=f'Venta #{v.id} (demo)'))
        v.total_venta = q(total)
        v.ganancia_total = q(ganancia)
        db.session.add(PagoVenta(venta_id=v.id, forma_pago_id=forma_id,
                                 monto=q(total), fecha=fecha))
        return v, q(total)

    venta_a, total_a = crear_venta(ahora - timedelta(days=2),
                                   [('P001', 2), ('P002', 1)],
                                   cli1, fp_efectivo, fp_efectivo.id)
    venta_b, total_b = crear_venta(ahora - timedelta(days=5),
                                   [('P005', 3), ('P003', 1)],
                                   None, fp_tarjeta, fp_tarjeta.id)
    venta_c, total_c = crear_venta(fecha_mes_pasado,
                                   [('P004', 1), ('P002', 2)],
                                   cli2, fp_transf, fp_transf.id)

    # ---- Devolucion de la venta B (1 x P005) ----
    fecha_dev = ahora - timedelta(days=1)
    sub_dev = q(productos['P005'].precio * 1)
    dev = Devolucion(venta_id=venta_b.id, fecha=fecha_dev,
                     motivo='Cable con defecto (demo)', monto_total=sub_dev)
    db.session.add(dev)
    db.session.flush()
    db.session.add(DetalleDevolucion(
        devolucion_id=dev.id, codigo_producto='P005', cantidad=1,
        subtotal=sub_dev))
    productos['P005'].stock += 1
    db.session.add(MovimientoInventario(
        codigo_producto='P005', tipo='devolucion', cantidad=1,
        fecha=fecha_dev, referencia=f'Devolucion #{dev.id} (demo)'))
    venta_b.total_venta = q(float(venta_b.total_venta) - sub_dev)

    # ---- Turno de caja cerrado con movimientos ----
    turno = TurnoCaja(
        caja_id=caja.id, usuario_id=admin.id,
        fecha_apertura=ahora - timedelta(days=2),
        fecha_cierre=ahora - timedelta(days=2) + timedelta(hours=8),
        saldo_inicial=200.00, saldo_final=q(200 + total_a - 50),
        estado='cerrado')
    db.session.add(turno)
    db.session.flush()
    db.session.add(MovimientoCaja(
        turno_id=turno.id, tipo='venta', monto=total_a,
        descripcion=f'Venta #{venta_a.id} (demo)',
        fecha=ahora - timedelta(days=2)))
    db.session.add(MovimientoCaja(
        turno_id=turno.id, tipo='egreso', monto=50.00,
        descripcion='Transporte de mercancia (demo)',
        fecha=ahora - timedelta(days=2) + timedelta(hours=2)))

    # ---- Promocion activa ----
    db.session.add(Promocion(
        codigo_producto='P003',
        descripcion='Liquidacion de audifonos',
        porcentaje=15.00,
        fecha_inicio=ahora - timedelta(days=2),
        fecha_fin=ahora + timedelta(days=7),
        activa=True))

    db.session.commit()

    print('Datos demo creados:')
    print(f'  - 2 proveedores, 2 clientes')
    print(f'  - {len(productos)} productos con entradas y kardex')
    print(f'  - 3 ventas: Q{total_a:.2f} (hoy-2d), Q{total_b:.2f} (hoy-5d), '
          f'Q{total_c:.2f} (mes pasado)')
    print(f'  - 1 devolucion (P005) + 1 turno cerrado + 1 promocion activa')
