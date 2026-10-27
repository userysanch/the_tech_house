# FASE 3: Front end completo — las 20 tablas visibles en pantalla

Esta fase cierra la rúbrica del proyecto: **cada una de las 20 tablas tiene una
pantalla del sistema que la muestra y/o la gestiona**, con permisos por rol
(`admin` / `empleado`), reportes con `GROUP BY` en la interfaz y datos de
demostración para ver todo con contenido.

## 1. Mapa: 20 tablas → pantallas

| # | Tabla | Pantalla (ruta) | Qué se ve / se hace | Rol |
|---|-------|-----------------|---------------------|-----|
| 1 | `roles` | Catálogos → Roles (`/catalogos/roles`) y `/usuarios` | Alta/baja de roles; selector al crear usuarios | admin |
| 2 | `categorias` | Catálogos → Categorías (`/catalogos/categorias`) + select en `/inventario` + `/reporte` | CRUD; agrupa el reporte por categoría | admin |
| 3 | `marcas` | Catálogos → Marcas (`/catalogos/marcas`) + select en `/inventario` | CRUD | admin |
| 4 | `proveedores` | Catálogos → Proveedores (`/catalogos/proveedores`) + select en `/entrada` | CRUD; queda ligado a cada compra | admin |
| 5 | `clientes` | Catálogos → Clientes (`/catalogos/clientes`) + select en `/caja` | CRUD; se elige al cobrar y queda en la venta | admin |
| 6 | `formas_pago` | Catálogos → Formas de pago (`/catalogos/formas_pago`) + botones en `/caja` | CRUD; botones con que se cobra (Efectivo/Tarjeta/Transferencia) | admin |
| 7 | `cajas` | `/caja` (caja física activa de la sesión) | Se usa al abrir/cerrar turno; historial en `/caja` | admin |
| 8 | `usuarios` | `/usuarios` | CRUD con contraseña encriptada y rol desde `roles` | admin |
| 9 | `productos` | `/inventario` + Buscador (`/buscador`) | CRUD completo con categoría, marca y proveedor | ambos |
| 10 | `entradas` | `/entrada` | Registrar compra (con proveedor), historial y kardex automático | ambos |
| 11 | `movimientos_inventario` | `/kardex` | Kardex filtrable (entrada/salida/devolución) + resumen `GROUP BY` | admin |
| 12 | `promociones` | `/promociones` (aplicadas en `/caja`) | CRUD, activar/desactivar; Caja muestra precio con descuento | admin |
| 13 | `ventas` | `/ventas` + `/caja` | Historial con detalle; el cobro crea la venta vía `SP_REGISTRARVENTA` | ambos |
| 14 | `detalle_ventas` | `/ventas` (detalle) y `/reporte` | Líneas de cada venta; alimenta los reportes | ambos |
| 15 | `pagos_venta` | `/ventas` (método) y `/caja` | Un pago por venta con su forma de pago y monto | ambos |
| 16 | `devoluciones` | `/devoluciones` | Armar devolución + historial; ejecuta `SP_APLICARDEVOLUCION` | admin |
| 17 | `detalle_devoluciones` | `/devoluciones` (detalle) | Líneas devueltas por venta (valida cantidades vendidas − devueltas) | admin |
| 18 | `ventas_pendientes` | Escáner móvil (`/scanner`) + carrito en `/caja` | Carrito temporal del escáner; se cobra desde Caja | ambos |
| 19 | `turnos_caja` | `/caja` | Abrir turno (saldo inicial) y cerrar vía `SP_CERRARCAJA` | admin |
| 20 | `movimientos_caja` | `/caja` | Ingresos/egresos manuales y ventas del turno; saldo en vivo | admin |

## 2. Pantallas nuevas de esta fase

### 2.1 Catálogos (`routes/catalogos.py` + `templates/catalogos.html`)

- Una sola pantalla con **6 pestañas**: categorías, marcas, proveedores,
  clientes, formas de pago y roles.
- CRUD genérico (dict `TIPOS`): validar longitud, unicidad de nombre donde
  aplica y `IntegrityError` si el registro está en uso (no se borra).
- Solo `admin`.

### 2.2 Kardex (`routes/kardex.py` + `templates/kardex.html`)

- Lista `movimientos_inventario` con filtro por tipo
  (entrada / salida / devolución).
- Encabezado resumen con `GROUP BY` (totales por tipo).
- Se alimenta solo: compras, ventas y devoluciones escriben el movimiento.

### 2.3 Caja completa (`routes/caja.py` + `templates/caja.html`)

- **Turno de caja**: abrir con saldo inicial; cerrar con `SP_CERRARCAJA`
  (`saldo_final = saldo_inicial + ingresos − egresos`).
- **Movimientos manuales** ingreso/egreso dentro del turno.
- **Cobro**: cliente (tabla `clientes`), forma de pago (tabla `formas_pago`)
  y carrito; el cobro ejecuta `SP_REGISTRARVENTA` en una sola transacción
  (venta + detalle + stock + kardex + pago + movimiento de caja), con
  ROLLBACK si no hay stock.
- **Promociones**: al buscar un producto se aplica la promoción activa y se
  muestra precio original + precio con descuento.
- `ventas_pendientes` del escáner móvil aparecen pendientes de cobro en Caja.

### 2.4 Devoluciones (`routes/devoluciones.py` + `templates/devoluciones.html`)

- Historial de `devoluciones` + `detalle_devoluciones`.
- Armar devolución desde una venta: valida cantidades (vendidas − ya
  devueltas) y ejecuta `SP_APLICARDEVOLUCION` (repone stock + kardex).

### 2.5 Usuarios (`routes/usuarios.py` + `templates/usuarios.html`)

- CRUD de `usuarios` con contraseña scrypt, selector de `roles` y bloqueo de
  autodelete. `base.html` muestra el rol del usuario desde la tabla `roles`.

### 2.6 Reportes con `GROUP BY` en la interfaz (`routes/reporte.py` + `templates/reporte.html`)

Tres tarjetas con consultas agregadas reales (no calculadas en Python):

- Ventas por categoría (`SUM`/`COUNT` agrupado por `Categoria.nombre`).
- Ventas por mes (`DATE_FORMAT('%Y-%m')`).
- Top 10 productos más vendidos (`TOP 10`).

## 3. Datos de demostración

- `python sembrar_demo.py` — siembra solo si la base está vacía:
  2 proveedores, 2 clientes, 6 productos con entradas y kardex, 3 ventas
  (2 de este mes y 1 del mes pasado), 1 devolución, 1 turno cerrado con
  movimientos y 1 promoción activa.
- `sqlcmd -S (local)\SQLEXPRESS -E -d TheTechHouse -i limpiar_demo.sql` —
  elimina lo demo y deja la base solo con los seeds de `schema.sql`.

## 4. Pruebas ejecutadas

- **49/49 checks** (`test_fases.py`): las 15 páginas responden 200, permisos
  de `empleado`, CRUD de catálogos, producto con categoría/marca/proveedor,
  entrada con kardex, turno + venta SP (stock 10→7, `pagos_venta`,
  `movimientos_caja`, kardex), venta sin stock rechazada con rollback,
  reportes con `GROUP BY`, devolución (stock 7→9), usuario con rol,
  promoción aplicada en Caja (15.00 → 13.50) y cierre de turno
  (saldo 145.00).
- **13/13 tablas de datos** con filas tras la siembra y **8/8 checks** de
  contenido de pantalla (kardex con compra/venta/devolución, historial de
  devoluciones, promo 174.00 → 147.90 en Caja, reportes con los 2 meses).

## 5. Archivos de esta fase

```
routes/catalogos.py    routes/kardex.py     routes/caja.py (reescrito)
routes/devoluciones.py routes/usuarios.py   routes/promociones.py
routes/reporte.py (GROUP BY)  routes/inventario.py  routes/entrada.py
templates/catalogos.html  kardex.html  devoluciones.html  usuarios.html
templates/promociones.html  caja.html  inventario.html  entrada.html
templates/reporte.html     base.html (menús + rol)
app.py (blueprints)  sembrar_demo.py  limpiar_demo.sql  FASE_3.md
```

```bash
# levantar
python app.py
# abrir https://localhost:5000 → login admin/admin123
```
