# FASE 1: Estructura del Proyecto, Dependencias, Script SQL y Configuración de Flask

## Estructura de Carpetas del Proyecto

```
the_tech_house/
├── templates/
├── static/
│   ├── css/
│   └── js/
├── app.py
├── requirements.txt
└── schema.sql
```

## Dependencias (requirements.txt)

```
Flask
Flask-SQLAlchemy
PyMySQL
```

**Instalación:**
```bash
pip install -r the_tech_house/requirements.txt
```

## Script SQL (schema.sql)

```sql
CREATE DATABASE IF NOT EXISTS the_tech_house_db;
USE the_tech_house_db;

CREATE TABLE IF NOT EXISTS productos (
    id INT AUTO_INCREMENT PRIMARY KEY,
    codigo VARCHAR(255) UNIQUE NOT NULL,
    nombre VARCHAR(255) NOT NULL,
    costo DECIMAL(10, 2) NOT NULL,
    margen DECIMAL(5, 2) NOT NULL,
    precio DECIMAL(10, 2) NOT NULL,
    stock INT NOT NULL
);

CREATE TABLE IF NOT EXISTS entradas (
    id INT AUTO_INCREMENT PRIMARY KEY,
    fecha DATETIME NOT NULL,
    codigo_producto VARCHAR(255) NOT NULL,
    cantidad INT NOT NULL,
    costo_unitario DECIMAL(10, 2) NOT NULL,
    FOREIGN KEY (codigo_producto) REFERENCES productos(codigo)
);

CREATE TABLE IF NOT EXISTS ventas (
    id INT AUTO_INCREMENT PRIMARY KEY,
    fecha DATETIME NOT NULL,
    total_venta DECIMAL(10, 2) NOT NULL,
    ganancia_total DECIMAL(10, 2) NOT NULL
);

CREATE TABLE IF NOT EXISTS detalle_ventas (
    id INT AUTO_INCREMENT PRIMARY KEY,
    venta_id INT NOT NULL,
    codigo_producto VARCHAR(255) NOT NULL,
    cantidad INT NOT NULL,
    precio_unitario DECIMAL(10, 2) NOT NULL,
    total DECIMAL(10, 2) NOT NULL,
    FOREIGN KEY (venta_id) REFERENCES ventas(id),
    FOREIGN KEY (codigo_producto) REFERENCES productos(codigo)
);
```

## Configuración de Flask (config.py + .env)

```python
import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

# Configuración de la base de datos MySQL
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'mysql+pymysql://root@localhost/the_tech_house')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Importar modelos y rutas aquí para evitar importaciones circulares
# from . import models, routes

if __name__ == '__main__':
    with app.app_context():
        db.create_all() # Crea las tablas si no existen
    app.run(debug=True)
```

En la implementación final, `config.py` carga primero el archivo `.env`
(local, ignorado por Git) y lee `DATABASE_URL` desde ahí: la contraseña de la
base de datos nunca queda escrita en el código fuente (requisito B4 de la
rúbrica). Ver `.env.example`.

---

**Próximo paso:** Espera a que el usuario diga "Continuar con la FASE 2" para proceder con los módulos backend y frontend.
