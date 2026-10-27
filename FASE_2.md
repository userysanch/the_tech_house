# FASE 2: Diseño de Base de Datos, API JSON, Procedimientos Almacenados y Documentación

Sistema **The Tech House** — Punto de Venta (POS) e Inventario para una tienda de
tecnología, construido con Flask + MySQL.

---

## 1. Descripción del problema

La tienda gestiona sus ventas e inventario de forma manual (libretas y hojas de
cálculo), lo que provoca:

- Desajustes entre el stock físico y el registrado (faltantes de mercancía no detectados).
- Errores de cálculo en precios, costos y ganancias (precios duplicados en distintas hojas).
- Cierre de caja lento y sin respaldo de los movimientos del día.
- Imposibilidad de saber qué se vende, a qué hora y con qué forma de pago.
- Pérdida del historial: no se puede responder "¿cuánto se vendió el mes pasado?".

El proyecto resuelve el problema con un sistema web que centraliza productos,
entradas de mercancía, ventas, caja y reportes en una sola base de datos
relacional, con validaciones y transacciones que impiden que una operación
incompleta deje la información inconsistente.

## 2. Usuarios del sistema

| Usuario | Rol | Acceso |
|---|---|---|
| Administrador | `admin` | Todo: productos, entradas, caja, reportes, exportaciones y API. |
| Vendedor / Cajero | `empleado` | Ventas, buscador, scanner, consulta de reportes. |

**Login por defecto:** `admin / admin123` y `vendedor / vendedor123`
(contraseñas con hash `werkzeug.security`, nunca en texto plano).

## 3. Necesidades funcionales

1. Registrar y actualizar productos con código, barras, costo, margen, precio y stock.
2. Registrar entradas de mercancía que actualicen el stock automáticamente.
3. Vender por escáner o teclado (carrito), con stock validado en el momento.
4. Cobrar en efectivo, tarjeta o transferencia y cerrar la caja del turno.
5. Registrar devoluciones que repongan el inventario.
6. Consultar reportes: ventas por categoría, por mes y productos más vendidos.
7. Exponer la información por una API JSON para integración con otros dispositivos
   (p. ej. el teléfono usado como escáner inalámbrico).

---

## 4. Reglas de negocio (5+)

1. **Todo producto tiene código único**; no se puede dar de alta dos veces el mismo
   código y su nombre y precio son obligatorios.
2. **No se puede vender más de lo que hay en stock**: si un ítem supera el stock, la
   venta completa se revierte (ROLLBACK) y no queda registrada.
3. **Toda venta modifica el inventario en la misma transacción**: cabecera, detalle,
   descuento de stock y kardex se confirman juntos o fallan juntos.
4. **Una entrada de mercancía siempre aumenta el stock** y queda registrada en el
   kardex (`movimientos_inventario`) con su fecha y referencia.
5. **Una devolución repone el stock** solo de los productos que pertenecen a esa
   venta y en la cantidad vendida; si el producto no estaba en la venta, se rechaza.
6. **El cierre de caja es una operación única**: `saldo_final = saldo_inicial +
   ingresos - egresos` del turno; una vez cerrado no admite movimientos.
7. **Solo un turno de caja queda abierto a la vez** para poder asociarle los cobros.

---

## 5. Modelo Entidad-Relación (20 tablas)

### 5.1 Inventario de tablas: PK y FK

| # | Tabla | PK | FK (columna → tabla) | Descripción |
|---|---|---|---|---|
| 1 | `roles` | `id` | — | Roles del sistema (admin, empleado). |
| 2 | `categorias` | `id` | — | Categorías de productos. |
| 3 | `marcas` | `id` | — | Marcas de productos. |
| 4 | `proveedores` | `id` | — | Proveedores de mercancía (nombre, NIT, contacto). |
| 5 | `clientes` | `id` | — | Clientes finales (NIT para facturación). |
| 6 | `formas_pago` | `id` | — | Efectivo, tarjeta, transferencia. |
| 7 | `usuarios` | `id` | `rol_id → roles.id` | Usuarios del sistema con hash de contraseña. |
| 8 | `productos` | `id` (único: `codigo`) | `categoria_id → categorias.id`, `marca_id → marcas.id`, `proveedor_id → proveedores.id` | Catálogo de artículos: costo, margen, precio, stock. |
| 9 | `entradas` | `id` | `codigo_producto → productos.codigo`, `proveedor_id → proveedores.id` | Compras de mercancía (entrada de stock). |
| 10 | `movimientos_inventario` | `id` | `codigo_producto → productos.codigo` | Kardex: entradas, salidas, ajustes y devoluciones. |
| 11 | `promociones` | `id` | `codigo_producto → productos.codigo` | Descuentos por producto con vigencia. |
| 12 | `ventas` | `id` | `cliente_id → clientes.id` | Cabecera de venta: fecha, total, ganancia. |
| 13 | `detalle_ventas` | `id` | `venta_id → ventas.id`, `codigo_producto → productos.codigo` | Ítems de cada venta (cantidad, precio, ganancia). |
| 14 | `pagos_venta` | `id` | `venta_id → ventas.id`, `forma_pago_id → formas_pago.id` | Pagos de cada venta (permite pago mixto). |
| 15 | `devoluciones` | `id` | `venta_id → ventas.id` | Cabecera de devolución con motivo y monto. |
| 16 | `detalle_devoluciones` | `id` | `devolucion_id → devoluciones.id`, `codigo_producto → productos.codigo` | Ítems devueltos. |
| 17 | `ventas_pendientes` | `id` | — (código de producto suelto) | Carrito temporal del escáner móvil. |
| 18 | `cajas` | `id` | — | Terminales físicas de cobro. |
| 19 | `turnos_caja` | `id` | `caja_id → cajas.id`, `usuario_id → usuarios.id` | Apertura/cierre de turno con saldos. |
| 20 | `movimientos_caja` | `id` | `turno_id → turnos_caja.id` | Ingresos, egresos y ventas del turno. |

### 5.2 Diagrama Entidad-Relación (texto)

```
roles ─┬─< usuarios >── turnos_caja >── cajas
       │       │              │
       │       │              └─< movimientos_caja
       │       │
categorias ┐    │
marcas ────┼─< productos >─┬─< entradas >──── proveedores
proveedores┘   │    │      └──────────────────────┘
               │    ├─< movimientos_inventario
               │    ├─< promociones
               │    └─< detalle_ventas >─ ventas >─ clientes
               │              │             ├─< pagos_venta >─ formas_pago
               │              │             └─< devoluciones >─ detalle_devoluciones ─┘
               └──────────────┘ (detalle_devoluciones → productos)

ventas_pendientes (carrito temporal, autónoma)
```

Convenciones: `─<` = relación uno-a-muchos (FK en el lado "muchos"),
`>─` = extremo "uno" de la relación.

---

## 6. Normalización hasta la Tercera Forma Normal (3FN)

**1FN — sin atributos multivalor ni repetidos.**
No existen columnas como "producto1, producto2": los ítems viven en
`detalle_ventas` / `detalle_devoluciones`, y los pagos múltiples en `pagos_venta`
(cada fila contiene un valor atómico).

**2FN — sin dependencias parciales.**
Las tablas de detalle tienen clave primaria simple (`id`); todos los atributos
dependen completamente de esa clave. En `detalle_ventas`, `precio_unitario`,
`cantidad`, `total` y `ganancia` se determinan por la pareja
(`venta_id`, `codigo_producto`); se les asignó un `id` surrogate que evita
cualquier dependencia parcial y permite renglones repetidos del mismo producto.

**3FN — sin dependencias transitivas.**
- El producto ya **no** almacena `categoria_nombre` ni `marca_nombre`: solo
  `categoria_id` / `marca_id` → la categoría depende de su clave, no del producto
  directamente (dependencia transitiva eliminada vía FK).
- `usuarios` almacena `rol_id → roles(nombre)`; el nombre del rol vive en `roles`.
- `ventas` almacena `total_venta` y `ganancia_total` como **datos derivados
  denormalizados** que se recalculan en el mismo momento de la venta dentro de
  `SP_REGISTRARVENTA`: son tolerados explícitamente por rendimiento, y la fuente
  de verdad sigue siendo `detalle_ventas` (verificado en los reportes, que suman
  desde el detalle). Ningún otro atributo no clave depende transitivamente de
  otro no clave.
- No hay redundancia de catálogos: `formas_pago`, `categorias`, `marcas`,
  `proveedores`, `clientes`, `roles` y `cajas` se referencian por id.

**Conclusión:** todas las tablas están en 3FN (todavía en BCN); no se detectan
anomalías de actualización, inserción o borrado en los catálogos.

### 6.1 Normalización detallada de tres tablas representativas

Requisito A8 de la rúbrica: dependencias funcionales (notación `X → Y` =
conocer X determina unívocamente a Y) y justificación del diseño final.

#### a) `detalle_ventas` — clave natural (`venta_id`, `codigo_producto`)

| Dependencia funcional | Análisis |
|---|---|
| `venta_id, codigo_producto → cantidad, precio_unitario, total, ganancia` | Los atributos dependen de la **clave completa** de la línea; no de una parte → cumple 2FN |
| `cantidad, precio_unitario → total` | `total = cantidad × precio_unitario`; se **almacena** para conservar el importe histórico aunque después cambie el precio de lista (no se recalcula al leer) |
| `venta_id, codigo_producto → ganancia` | `ganancia = precio_unitario − costo`; el costo **no** está en la tabla, evitando la transitiva `venta → producto → costo` (3FN) |

- **1FN:** valores atómicos (una cantidad por fila); no existen "producto1,
  producto2" ni una columna con los ítems de la venta.
- **Anomalías evitadas:** los datos de la cabecera (fecha, cliente, total)
  viven en `ventas`, no se repiten en cada línea; borrar una venta borra sus
  líneas (`ON DELETE CASCADE`).
- **Justificación del `id` surrogate:** evita renglones repetidos cuando un
  mismo producto aparece dos veces en la venta y mantiene una PK simple.

#### b) `productos` — clave natural `codigo` (UNIQUE)

| Dependencia funcional | Análisis |
|---|---|
| `codigo → nombre, costo, margen, precio, stock, codigo_barras, categoria_id, marca_id, proveedor_id` | Todo atributo no clave depende de la clave (PK simple ⇒ 2FN cumplida automáticamente) |
| ~~`categoria_id → categoria_nombre`~~ | **Eliminada:** `categoria_nombre` no existe; se resuelve con FK a `categorias` (3FN) |
| ~~`proveedor_id → proveedor_nombre, proveedor_nit`~~ | **Eliminada:** FK a `proveedores` (3FN) |
| `costo, margen → precio` | Derivado de negocio: `precio = costo × (1 + margen/100)`; se **almacena** para no recalcular en cada consulta y se **recalcula solo al editar** costo/margen (decisión documentada, no es redundancia accidental) |

#### c) `turnos_caja` — clave `id`

| Dependencia funcional | Análisis |
|---|---|
| `id → caja_id, usuario_id, fecha_apertura, fecha_cierre, saldo_inicial, saldo_final, estado` | PK simple ⇒ sin dependencias parciales (2FN) |
| `caja_id → cajas(nombre)` / `usuario_id → usuarios(nombre)` | No se copian los nombres al turno: FK a sus catálogos (3FN) |
| `saldo_final = saldo_inicial + SUM(movimientos.ingresos) − SUM(movimientos.egresos)` | **No** es una transitiva almacenada: el saldo se calcula **una sola vez** al cerrar el turno con `SP_CERRARCAJA` y se guarda como cierre de caja (auditoría); la fuente de verdad de los movimientos sigue siendo `movimientos_caja` |

- **Restricciones:** `estado ENUM('abierto','cerrado')`, `NOT NULL` en
  saldo_inicial y FKs — impiden datos inválidos (requisito técnico B4).


---

## 7. Procedimientos almacenados (con transacciones)

Archivo: `procedimientos.sql` (DELIMITER $$, todos con `START TRANSACTION`,
`SIGNAL SQLSTATE '45000'` para errores de negocio y `ROLLBACK ... RESIGNAL` ante
cualquier `SQLEXCEPTION`):

| Procedimiento | Parámetros | Qué hace (transacción atómica) |
|---|---|---|
| `SP_REGISTRARVENTA` | `cliente_id`, `forma_pago_id`, `items JSON`, `OUT venta_id` | Crea cabecera → valida stock con `SELECT ... FOR UPDATE` → inserta detalle → descuenta stock → escribe kardex (`salida`) → guarda pago → registra movimiento en caja si hay turno abierto. **Si falla un solo ítem, no se guarda nada.** |
| `SP_CERRARCAJA` | `turno_id` | Valida que el turno exista y esté abierto; calcula `saldo_final = saldo_inicial + ingresos - egresos` con `SUM()/CASE` sobre `movimientos_caja` y marca el turno como `cerrado`. |
| `SP_APLICARDEVOLUCION` | `venta_id`, `motivo`, `items JSON`, `OUT devolucion_id` | Valida que la venta y los ítems existan en ella → crea devolución → repone stock → escribe kardex (`devolucion`) → acumula el monto total. Todo o nada. |

Pruebas ejecutadas (datos eliminados al finalizar):
- Venta de 2 unidades → stock `10 → 8`, total y ganancia correctos.
- Venta con stock insuficiente → error 1644 y **rollback** (stock intacto).
- Devolución de las 2 unidades → stock `8 → 10`.
- Cierre de caja con turno de `100` + ingreso `50` − egreso `30` → `saldo_final = 120.00`.

---

## 8. API JSON (`routes/api.py`, prefijo `/api`)

**8 tablas administradas vía API** (catálogos + inventario + ventas):

| Método | Ruta | Tabla | Descripción |
|---|---|---|---|
| GET/POST | `/api/categorias` | `categorias` | Listar / crear. |
| GET/POST | `/api/marcas` | `marcas` | Listar / crear. |
| GET/POST | `/api/proveedores` | `proveedores` | Listar / crear. |
| GET/POST | `/api/clientes` | `clientes` | Listar / crear. |
| GET/POST | `/api/formas-pago` | `formas_pago` | Listar / crear formas de pago. |
| GET | `/api/productos?q=` | `productos` | Buscar por nombre, código o barras. |
| GET/POST/PUT/DELETE | `/api/productos/<codigo>` | `productos` | CRUD completo. |
| GET/POST | `/api/entradas` | `entradas` | Alta de mercancía (transacción: entrada + stock + kardex). |
| GET/POST | `/api/ventas` | `ventas` + `detalle_ventas` + `pagos_venta` | Alta vía `SP_REGISTRARVENTA`. |
| GET | `/api/ventas` | `ventas` | Últimas 200 ventas con detalle y pagos. |
| POST | `/api/devoluciones` | `devoluciones` | Vía `SP_APLICARDEVOLUCION`. |
| GET | `/api/reporte/ventas-por-categoria` | — | Reporte `GROUP BY`. |
| GET | `/api/reporte/ventas-por-mes` | — | Reporte `GROUP BY`. |
| GET | `/api/reporte/top-productos` | — | Reporte `GROUP BY ... LIMIT 10`. |

- Las lecturas son públicas; las mutaciones exigen sesión iniciada (401 JSON si no).
- Errores de negocio → HTTP 400/409 con `{"ok": false, "mensaje": "..."}`.
- Ejemplo: `POST /api/ventas`

```json
{"cliente_id": 1, "forma_pago_id": 1,
 "items": [{"codigo": "P001", "cantidad": 2, "precio": 15.00}]}
→ 201 {"ok": true, "venta": {...}, "detalles": [...]}
```

---

## 9. Reportes con funciones de agrupación (GROUP BY)

| Endpoint | Agrupación | Funciones |
|---|---|---|
| `/api/reporte/ventas-por-categoria` | `Categoria.nombre` (JOIN categorias→productos→detalle_ventas→ventas) | `COUNT`, `SUM(total)`, `SUM(ganancia)` |
| `/api/reporte/ventas-por-mes` | `DATE_FORMAT(fecha,'%Y-%m')` | `COUNT(ventas)`, `SUM(total_venta)`, `SUM(ganancia_total)` |
| `/api/reporte/top-productos` | `productos.codigo, productos.nombre` | `SUM(cantidad)` + `ORDER BY ... DESC LIMIT 10` |

(Ejemplo real de la prueba: `{"categoria": "CAT_TEST", "items_vendidos": 1,
"total_ventas": 30.0, "ganancia": 10.0}`.)

---

## 10. Archivos de esta fase y cómo ejecutarlos

```
the_tech_house/
├── schema.sql          → 20 tablas + seeds (roles, formas_pago, categorias, marcas, cajas, usuarios)
├── procedimientos.sql  → SP_REGISTRARVENTA, SP_CERRARCAJA, SP_APLICARDEVOLUCION
├── models/__init__.py  → 20 modelos ORM (uno por tabla)
├── routes/api.py       → API JSON + reportes GROUP BY (blueprint `api_bp`)
└── FASE_2.md           → este documento
```

Instalación desde cero:

```bash
mysql -u root -p < schema.sql
mysql -u root -p < procedimientos.sql
python app.py
# Abrir https://localhost:5000 → login admin/admin123
```

`python app.py` ejecuta además `db.create_all()` (solo crea tablas faltantes; el
esquema completo ya está en `schema.sql`) y crea los usuarios por defecto si no
existen.

**Nota técnica:** la versión de SQLAlchemy debe ser **2.0.x** (`pip install
"sqlalchemy>=2.0,<2.1"`), porque la 2.1.x exige sus extensiones compiladas (.pyd)
y en este equipo una directiva de Control de aplicaciones de Windows las bloquea;
la 2.0.x usa sus implementaciones en Python puro cuando las .pyd no cargan.
