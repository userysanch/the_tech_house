# The Tech House - Sistema POS e Inventario

Sistema de Punto de Venta (POS) e Inventario desarrollado con Flask, Microsoft SQL Server y Bootstrap 5.

**Repositorio:** https://github.com/userysanch/the_tech_house

## 🛠️ Stack Tecnológico

- **Backend:** Python con Flask
- **Base de Datos:** Microsoft SQL Server 2022 Express (T-SQL)
- **ORM:** Flask-SQLAlchemy + pyodbc
- **Frontend:** HTML5, CSS3, JavaScript y Bootstrap 5
- **Diseño:** Interfaz responsiva con encabezados azul oscuro

## 📋 Requisitos Previos

- Python 3.10+
- Microsoft SQL Server 2022 Express (instancia local, ej. `(local)\SQLEXPRESS`)
- ODBC Driver 18 for SQL Server
- pip (gestor de paquetes de Python)

## 🚀 Instalación

### 1. Clonar o descargar el proyecto

```bash
cd the_tech_house
```

### 2. Crear un entorno virtual (opcional pero recomendado)

```bash
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate
```

### 3. Instalar las dependencias

```bash
pip install -r requirements.txt
```

### 4. Crear la base de datos

Ejecuta los scripts T-SQL (crea la base `TheTechHouse`, 20 tablas + datos
iniciales y los 3 procedimientos almacenados):

```bat
sqlcmd -S (local)\SQLEXPRESS -E -i schema.sql
sqlcmd -S (local)\SQLEXPRESS -E -i procedimientos.sql
```

O copia y pega el contenido de cada archivo en SQL Server Management Studio.

### 5. Configurar la conexión a la base de datos

La conexión usa autenticación de Windows (sin contraseñas en el código).
Copia el archivo de ejemplo como `.env` si necesitas ajustar la instancia
(el `.env` es local: `.gitignore` impide que se suba a Git):

```bat
copy .env.example .env
```

Contenido por defecto (ya funciona en una instalación estándar):

```
DATABASE_URL=mssql+pyodbc://@localhost\SQLEXPRESS/TheTechHouse?driver=ODBC+Driver+18+for+SQL+Server&TrustServerCertificate=yes
SECRET_KEY=una_clave_secreta_cualquiera
```

La aplicación (`config.py`) lee ese archivo al arrancar.

### 6. Ejecutar la aplicación

```bash
python app.py
```

La aplicación estará disponible en `http://localhost:5000`

## 📱 Módulos y Funcionalidades

### 1. **Menú Principal (Dashboard)**
- Acceso rápido a todos los módulos
- Interfaz intuitiva con botones grandes

### 2. **Entrada**
- Registrar ingreso de mercancía
- Actualizar automáticamente el stock
- Historial de entradas

### 3. **Inventario**
- CRUD completo de productos
- Crear, editar y eliminar productos
- Cálculo automático de precios según margen
- Visualización del stock

### 4. **Caja (Punto de Venta)**
- Búsqueda de productos por código
- Carrito de compras temporal
- Cálculo de totales y ganancias
- Registro de ventas con descuento automático de stock

### 5. **Ventas**
- Historial de todas las ventas realizadas
- Detalles de cada transacción

### 6. **Reporte**
- Análisis de ganancias
- Visualización de ventas y costos
- Totales de ventas y ganancias

### 7. **Catálogos**
- Pantalla única con pestañas: Categorías, Marcas, Proveedores, Clientes,
  Formas de pago y Roles
- CRUD completo con validaciones (solo administrador)

### 8. **Kardex**
- Historial de `movimientos_inventario` con filtro por tipo
  (entrada / salida / devolución)
- Resumen de totales por tipo (agrupado en SQL con `GROUP BY`)

### 9. **Devoluciones**
- Historial de devoluciones y armado de una nueva sobre una venta
- Ejecuta `SP_APLICARDEVOLUCION` (repone stock y kardex en transacción)

### 10. **Usuarios y Promociones**
- CRUD de usuarios con contraseña encriptada y rol asignado
- Promociones con vigencia y descuento aplicado automáticamente al cobrar

### 11. **Buscador**
- Búsqueda rápida de productos
- Filtrado por código o nombre

## 🎯 Las 20 tablas en pantalla

Cada tabla del modelo tiene una pantalla que la muestra o gestiona. El mapa
completo (tabla → ruta → rol) está en [`FASE_3.md`](FASE_3.md).

## 🌱 Datos de demostración

```bash
python sembrar_demo.py                                    # sembrar (solo si la BD está vacía)
sqlcmd -S (local)\SQLEXPRESS -E -d TheTechHouse -i limpiar_demo.sql   # borrar lo demo
```

Incluye proveedores, clientes, 6 productos con kardex, 3 ventas (dos de este
mes y una del mes pasado), una devolución, un turno cerrado y una promoción
activa: reportes, kardex y caja quedan con contenido.

## 📊 Estructura de la Base de Datos

**20 tablas relacionadas** en 3FN. El detalle completo de PK/FK, el diagrama
Entidad-Relación, las reglas de negocio y el análisis de normalización están en
[`FASE_2.md`](FASE_2.md).

Resumen por módulos:

| Módulo | Tablas |
|---|---|
| Catálogos | `roles`, `categorias`, `marcas`, `proveedores`, `clientes`, `formas_pago`, `cajas` |
| Usuarios | `usuarios` |
| Inventario | `productos`, `entradas`, `movimientos_inventario`, `promociones` |
| Ventas | `ventas`, `detalle_ventas`, `pagos_venta`, `devoluciones`, `detalle_devoluciones`, `ventas_pendientes` |
| Caja | `turnos_caja`, `movimientos_caja` |

### Procedimientos almacenados (`procedimientos.sql`, T-SQL)

Los tres SP siguen el patrón de clase: `SET NOCOUNT ON` → `BEGIN TRY` →
`BEGIN TRANSACTION` → validaciones con `THROW` → trabajo → `COMMIT` →
`BEGIN CATCH` con `IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION` y `THROW`.

- `SP_REGISTRARVENTA` — venta completa (cabecera, detalle, stock, kardex, pago y
  caja) en **una sola transacción**; recibe los renglones como tipo de tabla
  (`TIPODETALLEVENTA`) y devuelve el ID por parámetro OUTPUT; hace ROLLBACK si
  el stock no alcanza.
- `SP_CERRARCAJA` — calcula `saldo_final = saldo_inicial + ingresos - egresos`.
- `SP_APLICARDEVOLUCION` — devuelve mercancía y repone el stock en transacción.

### API JSON (prefijo `/api`)

CRUD de `categorias`, `marcas`, `proveedores`, `clientes`, `productos`,
`formas_pago`, `entradas` (alta transaccional), `ventas` (vía
`SP_REGISTRARVENTA`) y `devoluciones`, más reportes con `GROUP BY`:

- `GET /api/reporte/ventas-por-categoria`
- `GET /api/reporte/ventas-por-mes`
- `GET /api/reporte/top-productos`

Las lecturas son públicas; las mutaciones requieren sesión iniciada.

## 🎨 Características de Diseño

- Interfaz limpia y moderna
- Encabezados azul oscuro (#1a3a52)
- Fondos blancos y grises claros
- Navegación intuitiva en la parte superior
- Diseño responsivo para dispositivos móviles
- Botones grandes y accesibles

## 📝 Notas Importantes

1. **Seguridad:** Este es un proyecto de demostración. Para producción, implementa autenticación y validación adicional.
2. **Respaldos:** Realiza respaldos regulares de tu base de datos.
3. **Configuración:** Actualiza las credenciales de la base de datos según tu entorno.

## 🐛 Solución de Problemas

### Error: "No module named 'flask'"
```bash
pip install -r requirements.txt
```

### Error: "Can't connect to SQL Server"
- Verifica que el servicio `MSSQL$SQLEXPRESS` esté ejecutándose
- Comprueba que el driver ODBC 18 esté instalado
- Asegúrate de que la base `TheTechHouse` existe (`sqlcmd ... -Q "SELECT name FROM sys.databases"`)

### Error: "404 Not Found"
- Verifica que todas las rutas estén correctamente importadas en `app.py`
- Comprueba que los archivos de plantilla existan en la carpeta `templates/`

## 📞 Soporte

Para reportar problemas o sugerencias, por favor crea un issue en el repositorio.

## 📄 Licencia

Este proyecto es de código abierto y está disponible bajo la licencia MIT.

---

**Versión:** 4.0.0  
**Última actualización:** 2026-10-27
