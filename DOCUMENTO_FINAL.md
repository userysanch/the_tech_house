# Documento final del proyecto (material para el PDF)

> **The Tech House — Diseño e Implementación de una Base de Datos y una API**
>
> Instrucciones: copia este contenido a Word o Google Docs, dale el formato
> de tu curso y exporta a PDF. Reemplaza `[LINK_DEL_REPOSITORIO]` con la URL
> de tu repositorio en GitHub. Detalles técnicos ampliados en
> `FASE_1.md`, `FASE_2.md` y `FASE_3.md`.

---

## 1. Descripción del problema

La tienda de tecnología gestiona sus ventas e inventario de forma manual
(libretas y hojas de cálculo), lo que provoca:

- Desajustes entre el stock físico y el registrado (faltantes de mercancía
  no detectados).
- Errores de cálculo en precios, costos y ganancias (precios duplicados en
  distintas hojas).
- Cierre de caja lento y sin respaldo de los movimientos del día.
- Imposibilidad de saber qué se vende, con qué forma de pago y a qué hora.
- Pérdida del historial: no se puede responder *"¿cuánto se vendió el mes
  pasado?"*.

## 2. Objetivo

Diseñar e implementar una solución de software que administre la información
de la tienda mediante una **base de datos relacional normalizada (20 tablas,
3FN)** y una **API JSON** que permita consultar, crear, actualizar y
eliminar registros, ejecutar operaciones de negocio con **procedimientos
almacenados y transacciones**, y generar **reportes con funciones de
agrupación (GROUP BY)**.

## 3. Alcance

- Punto de venta (POS) con carrito, stock validado y cobro por forma de pago.
- Inventario: productos, entradas de mercancía, kardex y promociones.
- Caja: turnos, movimientos de ingreso/egreso y cierre con saldo.
- Devoluciones que repone inventario.
- Reportes: ventas por categoría, por mes y productos más vendidos.
- API JSON con CRUD y los mismos reportes, para integración (p. ej. teléfono
  como escáner inalámbrico).
- **Fuera de alcance:** facturación electrónica, multi-almacén y compras a
  crédito.

## 4. Usuarios del sistema

| Usuario | Rol | Acceso |
|---|---|---|
| Administrador | `admin` | Todo: catálogos, productos, entradas, caja, devoluciones, reportes, usuarios y API |
| Vendedor / Cajero | `empleado` | Ventas, buscador, escáner y consulta de reportes |

Login de prueba: `admin / admin123` y `vendedor / vendedor123`
(contraseñas con hash, nunca en texto plano).

## 5. Necesidades funcionales

1. Registrar y actualizar productos con código, barras, costo, margen, precio y stock.
2. Registrar entradas de mercancía que actualicen el stock automáticamente.
3. Vender por escáner o teclado (carrito), con stock validado en el momento.
4. Cobrar en efectivo, tarjeta o transferencia y cerrar la caja del turno.
5. Registrar devoluciones que repone el inventario.
6. Consultar reportes: ventas por categoría, por mes y productos más vendidos.
7. Exponer la información por API JSON para integración con otros dispositivos.

## 6. Reglas de negocio

1. **Todo producto tiene código único**; no se puede dar de alta dos veces el
   mismo código.
2. **No se puede vender más de lo que hay en stock**: si un ítem supera el
   stock, la venta completa se revierte (ROLLBACK).
3. **Toda venta modifica el inventario en la misma transacción**: cabecera,
   detalle, descuento de stock, kardex, pago y movimiento de caja se
   confirman juntos o fallan juntos.
4. **Una entrada de mercancía siempre aumenta el stock** y queda registrada
   en el kardex con fecha y referencia.
5. **Una devolución repone el stock** solo de los productos y en las
   cantidades que pertenecen a esa venta.
6. **El cierre de caja es una operación única**:
   `saldo_final = saldo_inicial + ingresos − egresos`; cerrado el turno no
   admite movimientos.
7. **Solo un turno de caja queda abierto a la vez**.

## 7. Modelo entidad-relación y las 20 tablas

El diagrama completo (entidades, atributos, relaciones y cardinalidades)
está en `FASE_2.md`, sección 5. Resumen por módulo — **cada tabla tiene
función justificada y pantalla en el sistema** (ver `FASE_3.md`):

| Módulo | Tablas | Función |
|---|---|---|
| Catálogos | `roles`, `categorias`, `marcas`, `proveedores`, `clientes`, `formas_pago`, `cajas` | Datos maestros referenciados por FK desde el resto del modelo |
| Usuarios | `usuarios` | Quién opera el sistema (contraseña con hash, rol desde `roles`) |
| Inventario | `productos`, `entradas`, `movimientos_inventario`, `promociones` | Artículos, compras, kardex (trazabilidad) y descuentos |
| Ventas | `ventas`, `detalle_ventas`, `pagos_venta`, `devoluciones`, `detalle_devoluciones`, `ventas_pendientes` | Cabecera/líneas de venta, cobros, devoluciones y carrito del escáner |
| Caja | `turnos_caja`, `movimientos_caja` | Apertura/cierre y movimientos del turno |

Ninguna tabla es artificial: todas representan entidades o eventos reales
del negocio y están conectadas por claves primarias y foráneas.

## 8. Normalización

- **1FN:** sin columnas multivalor ni repetidas (los ítems viven en
  `detalle_ventas`; los pagos en `pagos_venta`).
- **2FN:** sin dependencias parciales (claves simples o atributos que
  dependen de la clave completa).
- **3FN:** sin dependencias transitivas (categoría, marca y proveedor viven
  en sus tablas, referenciadas por FK; el nombre del rol en `roles`).

Tres tablas representativas (`detalle_ventas`, `productos`, `turnos_caja`)
están analizadas con sus **dependencias funcionales** en `FASE_2.md`
sección 6.1.

## 9. Procedimientos almacenados y transacciones

| SP | Operación | Cambios relacionados | Garantía |
|---|---|---|---|
| `sp_registrar_venta` | Registrar venta y actualizar existencias | `ventas` + `detalle_ventas` + `pagos_venta` + stock + `movimientos_inventario` + `movimientos_caja` | Valida stock; COMMIT o ROLLBACK completo |
| `sp_cerrar_caja` | Cerrar turno con saldo | Calcula `saldo_final` desde `movimientos_caja` y cambia `turnos_caja.estado` | Operación única, turno cerrado queda inmutable |
| `sp_aplicar_devolucion` | Aplicar devolución | `devoluciones` + `detalle_devoluciones` + repone stock + kardex | Valida cantidades vendidas − devueltas; COMMIT/ROLLBACK |

Se invocan desde la API (`POST /api/ventas`, `POST /api/devoluciones`) y
desde las pantallas de Caja y Devoluciones.

## 10. API JSON

- **CRUD en 9 tablas** (≥5 requeridas): `categorias`, `marcas`,
  `proveedores`, `clientes`, `productos`, `formas_pago`, `entradas`,
  `ventas` y `devoluciones`, cada operación con su endpoint, validación de
  datos y respuestas HTTP (200, 201, 400, 404, 409).
- **Reportes con agrupación** (≥2 requeridos):
  - `GET /api/reporte/ventas-por-mes` — `SUM`, `COUNT`, `GROUP BY` con `DATE_FORMAT`.
  - `GET /api/reporte/ventas-por-categoria` — `SUM`/`COUNT` agrupado por categoría.
  - `GET /api/reporte/top-productos` — `SUM` agrupado por producto con `LIMIT`.
- Documentación de endpoints y parámetros en `FASE_2.md` sección 8.
- Las credenciales de la base **no están en el código**: viven en `.env`
  (ignorado por Git).

## 11. Datos de prueba

El repositorio incluye `schema.sql` (20 tablas + seeds), `procedimientos.sql`
(3 SPs) y `sembrar_demo.py`, que siembra proveedores, clientes, 6 productos
con kardex, 3 ventas (dos de este mes y una del mes pasado), una devolución,
un turno cerrado y una promoción activa — para que reportes, kardex y caja
se vean con contenido. `limpiar_demo.sql` permite volver al estado inicial.

## 12. Entregables

1. **Este documento PDF** (problema, objetivo, alcance, reglas de negocio y
   link del repositorio).
2. **Repositorio en GitHub:** [LINK_DEL_REPOSITORIO]
   - Diagrama entidad-relación (`FASE_2.md` §5).
   - Script SQL (`schema.sql`, `procedimientos.sql`).
   - Código fuente de la API (`routes/`, `models/`, `app.py`, `config.py`).
   - Instrucciones de instalación y ejecución (`README.md`).
   - Documentación de fases (`FASE_1.md`, `FASE_2.md`, `FASE_3.md`) y
     guion de demostración (`GUION_DEMO.md`).

## 13. Cómo ejecutarlo

```bash
# 1. Dependencias
python -m pip install -r requirements.txt

# 2. Base de datos
mysql -u root -p < schema.sql
mysql -u root -p < procedimientos.sql

# 3. Credenciales (no van en el código)
copy .env.example .env     # y editar con tu password de MySQL

# 4. Datos de demostración (opcional)
python sembrar_demo.py

# 5. Arrancar
python app.py              # → https://localhost:5000
```
