# Guion de demostración — The Tech House

Guía para explicarle al ingeniero **qué es el sistema, dónde están las 20
tablas y cómo funciona**, y para hacer la demo en vivo sin nervios.
Credenciales: `admin` / `admin123` (rol admin) y `vendedor` / `vendedor123`
(rol empleado).

---

## 1. Las 20 tablas: cuáles son, qué función cumplen y dónde se ven

> Pregunta típica: *"¿Cuáles son sus 20 tablas y qué hace cada una?"*
> Respuesta corta: son tablas del modelo de un POS de tecnología: 7 de
> catálogo, 1 de usuarios, 4 de inventario, 6 de ventas y 2 de caja. Cada
> una tiene pantalla en el sistema — las recorro en el menú.

| # | Tabla | Función (qué guarda) | Dónde se ve en pantalla |
|---|-------|----------------------|--------------------------|
| 1 | `roles` | Permisos: admin y empleado | Catálogos → Roles; y el selector en Usuarios |
| 2 | `categorias` | Agrupan productos y alimentan el reporte por categoría | Catálogos → Categorías; combo en Inventario |
| 3 | `marcas` | Marca de cada producto | Catálogos → Marcas; combo en Inventario |
| 4 | `proveedores` | Quién nos vende (NIT, contacto) | Catálogos → Proveedores; combo en Entrada |
| 5 | `clientes` | A quién le vendemos | Catálogos → Clientes; combo al cobrar en Caja |
| 6 | `formas_pago` | Efectivo, Tarjeta, Transferencia | Catálogos → Formas de pago; botones al cobrar |
| 7 | `cajas` | La caja física del negocio | Se usa al abrir/cerrar turno en Caja |
| 8 | `usuarios` | Quién entra al sistema (contraseña encriptada) | Usuarios (solo admin) |
| 9 | `productos` | Artículo: código, costo, margen, precio, stock | Inventario (CRUD) y Buscador |
| 10 | `entradas` | Compras de mercancía a proveedores | Entrada (registrar + historial) |
| 11 | `movimientos_inventario` | **Kardex**: cada entrada, salida y devolución | Kardex (filtro por tipo + resumen) |
| 12 | `promociones` | Descuentos con vigencia por producto | Promociones; aplicados al buscar en Caja |
| 13 | `ventas` | Cabecera de cada venta (fecha, total, ganancia) | Ventas (historial) y el cobro en Caja |
| 14 | `detalle_ventas` | Líneas de la venta: cantidad × precio | Detalle de cada venta en Ventas |
| 15 | `pagos_venta` | Cuánto se pagó y con qué forma de pago | En el detalle de la venta |
| 16 | `devoluciones` | Cabecera de la devolución (motivo, fecha) | Devoluciones (historial + armar) |
| 17 | `detalle_devoluciones` | Qué producto y cuántas unidades se devolvieron | Detalle en Devoluciones |
| 18 | `ventas_pendientes` | Carrito del escáner móvil pendiente de cobrar | Escáner → aparece en Caja para cobrar |
| 19 | `turnos_caja` | Apertura y cierre de caja con saldo | Tarjeta "Turno de Caja" en Caja |
| 20 | `movimientos_caja` | Ingresos, egresos y ventas del turno | En Caja, debajo del turno |

> Si pregunta **"¿no es artificial?"**: cada tabla nace de una entidad real
> del negocio (lo que compramos, lo que vendemos, con quién, quién cobra) y
> todas están referenciadas por PK/FK — ninguna existe solo para cumplir el
> número 20.

---

## 2. Demo en vivo (~5 minutos)

### Paso 0 — Contexto (30 segundos)
*"Es un punto de venta e inventario para una tienda de tecnología: 20
tablas relacionadas en 3FN, API JSON, 3 procedimientos almacenados con
transacciones y reportes con GROUP BY. Los datos de prueba ya están
sembrados, así que todo se ve con contenido."*

### Paso 1 — Catálogos (30 s)
1. Menú **Catálogos** → pestañas: Categorías, Marcas, Proveedores, Clientes,
   Formas de pago, Roles.
2. *"Aquí están las tablas 1 a 6. CRUD completo, solo admin; si intento borrar
   algo que está en uso, la restricción FK lo impide."*
3. Mostrar un registro (p. ej. proveedor "Distribuidora Tech GT").

### Paso 2 — Inventario: ingresar datos (45 s)
1. Menú **Inventario** → **Nuevo producto**: código `DEMO01`, nombre
   "Audífonos Demo", costo 100, margen 40 (precio queda 140), categoría
   **Electronica**, marca **Genius**.
2. Guardar → aparece en la lista.
3. *"Tabla `productos` (9). Los combos de categoría/marca/proveedor son las
   FK; el precio se calcula del margen."*

### Paso 3 — Entrada de mercancía (45 s)
1. Menú **Entrada** → escanear o escribir el código de `DEMO01`, cantidad 10,
   costo 100, proveedor **Distribuidora Tech GT** → Guardar.
2. *"Tabla `entradas` (10). El alta es transaccional: registra la compra,
   actualiza el stock y escribe el kardex."*
3. Menú **Kardex** → aparece el movimiento tipo **entrada**.

### Paso 4 — Venta en Caja (1 min) ⭐ lo más importante
1. Menú **Caja** → **Abrir turno** con saldo inicial `200`.
   → Tablas `cajas` + `turnos_caja` (7 y 19).
2. Buscar `DEMO01` (o `P001`) → se agrega al carrito. Si hay promoción
   activa, muestra precio con descuento (tabla `promociones`, 12).
3. Seleccionar **Cliente** (tabla `clientes`, 5) y **forma de pago**
   "Efectivo" (tabla `formas_pago`, 6).
4. **Cobrar** → mensaje *"Venta registrada. Total: Q…"*.
   *"Detrás se ejecutó `sp_registrar_venta`: en UNA transacción creó
   `ventas`, `detalle_ventas`, `pagos_venta`, bajó el stock, escribió el
   kardex y el movimiento de caja. Si no hubiera stock, haría ROLLBACK
   completo."*
5. Verificar: en **Kardex** aparece la salida; en la tarjeta de turno subió
   el saldo; en **Ventas** aparece la venta con su detalle y pago.

### Paso 5 — Devolución (45 s)
1. Menú **Devoluciones** → elegir la venta anterior → producto `DEMO01`,
   cantidad 1 → motivo "Prueba" → **Aplicar**.
   → *"Ejecuta `sp_aplicar_devolucion`: repone el stock y escribe el kardex
   en transacción. Valida que no se devuelva más de lo vendido."*
2. Verificar: en Inventario el stock de `DEMO01` subió; en Kardex aparece
   tipo **devolución**; en Devoluciones quedó el historial (tablas 16 y 17).

### Paso 6 — Cerrar caja (30 s)
1. En Caja → **Cerrar turno**.
   → *"`sp_cerrar_caja` calcula saldo_final = saldo_inicial + ingresos −
   egresos con los movimientos del turno (tabla 20) y guarda el cierre
   (tabla 19)."*

### Paso 7 — Reportes con GROUP BY (30 s)
1. Menú **Reporte** → sección **"Reportes agrupados (GROUP BY en SQL)"**:
   - Ventas por categoría (`SUM`/`COUNT` agrupado),
   - Ventas por mes (`DATE_FORMAT`),
   - Top 10 productos (`LIMIT`).
2. *"Estas tres consultas corren en MySQL con GROUP BY; los mismos datos
   están en los endpoints `/api/reporte/…`."*

### Paso 8 — La API (30 s)
En el navegador o con `curl`:

```
GET  /api/productos          → lista (Read)
GET  /api/productos/1        → uno (Read específico)
POST /api/productos          → crea (Create)
PUT  /api/productos/1        → actualiza (Update)
DELETE /api/productos/1      → elimina (Delete)
GET  /api/reporte/ventas-por-mes          → GROUP BY
GET  /api/reporte/ventas-por-categoria    → GROUP BY
GET  /api/reporte/top-productos           → GROUP BY
```

*"CRUD completo en más de cinco tablas (categorías, marcas, proveedores,
clientes, productos, formas de pago, entradas, ventas, devoluciones), con
validación de datos y códigos HTTP 200/400/409."*

---

## 3. Preguntas típicas del evaluador y posibles respuestas

**¿Por qué 20 tablas y no menos?**
Porque el negocio real las pide: catálogos (roles, categorías, marcas,
proveedores, clientes, formas de pago, cajas), personas (usuarios),
inventario (productos, entradas, kardex, promociones), ventas (ventas,
detalle, pagos, devoluciones, detalle de devoluciones, pendientes del
escáner) y caja (turnos, movimientos). Todas están referenciadas por PK/FK
— ninguna es artificial.

**¿Qué hace `sp_registrar_venta`?**
Recibe cliente, forma de pago y el arreglo de ítems; en una sola transacción
crea la venta, sus líneas, el pago, descuenta el stock, escribe el kardex y
el movimiento de caja; si algo falla (p. ej. stock insuficiente) hace
ROLLBACK y no queda nada a medias. Se invoca desde el endpoint
`POST /api/ventas` y desde el cobro de Caja.

**¿Cuándo veo un ROLLBACK?**
En la demo: intentar cobrar un producto con más unidades que las que hay —
el SP valida antes de confirmar y devuelve *"Stock insuficiente"* sin
modificar nada.

**¿Qué hace `sp_cerrar_caja`?**
Suma los movimientos del turno: `saldo_final = saldo_inicial + ingresos −
egresos` y cambia el estado a cerrado.

**¿Qué hace `sp_aplicar_devolucion`?**
Valida que las unidades devueltas no superen lo vendido, inserta la
devolución y su detalle, repone el stock y registra el movimiento de kardex
— todo en una transacción.

**¿Qué es el kardex?**
La tabla `movimientos_inventario`: cada entrada, salida y devolución de
stock con fecha y referencia (Compra #, Venta #, Devolución #). Es la
trazabilidad de la mercancía.

**¿Dónde está la normalización?**
En FASE_2.md: 1FN (sin columnas repetidas), 2FN (claves simples/dependencias
completas) y 3FN (sin transitivas: categoría y marca viven en sus tablas,
no como texto en el producto), con tres tablas analizadas en detalle con
dependencias funcionales.

**¿Y el diagrama entidad-relación?**
En FASE_2.md, sección 5: entidades, atributos, relaciones y cardinalidades
de las 20 tablas.

**¿Cómo evitas contraseñas en el código?**
En `.env`, que está en `.gitignore` y nunca se sube; `config.py` lo lee al
arrancar. En la base, las contraseñas se guardan con hash scrypt.

**¿Por qué usas MySQL si el PDF dice "preferiblemente SQL Server"?**
El PDF dice *preferiblemente*; MySQL cumple todo lo obligatorio: relación,
PK/FK, restricciones, procedimientos almacenados y transacciones. El
código del API y los SPs son transportables.

---

## 4. Checklist antes de la defensa

- [ ] BD sembrada (`python sembrar_demo.py`) → reportes y kardex con datos
- [ ] Servidor corriendo: `python app.py` → `https://localhost:5000`
- [ ] Probar el guion completo una vez (crear → entrada → vender → devolver → cerrar)
- [ ] Saber explicar las 20 tablas con la tabla de la sección 1
- [ ] Saber qué hace cada uno de los 3 SPs
- [ ] Documento PDF listo con el **link del repositorio de GitHub**
