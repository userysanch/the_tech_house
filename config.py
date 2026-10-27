import os

# ---------------------------------------------------------------------------
# Carga de variables de entorno desde el archivo .env (no se versiona en Git).
# Formato: CLAVE=valor  (lineas vacias o que empiezan con # se ignoran)
# ---------------------------------------------------------------------------
def _cargar_env():
    ruta = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
    if not os.path.isfile(ruta):
        return
    with open(ruta, encoding='utf-8') as archivo:
        for linea in archivo:
            linea = linea.strip()
            if not linea or linea.startswith('#') or '=' not in linea:
                continue
            clave, valor = linea.split('=', 1)
            os.environ.setdefault(clave.strip(), valor.strip())


_cargar_env()


class Config:
    # Clave secreta de sesiones (definida en .env)
    SECRET_KEY = os.environ.get('SECRET_KEY', 'the_tech_house_secret_key_2026')

    # Base de datos: Microsoft SQL Server (SQLEXPRESS).
    # La contrasena NUNCA se escribe en el codigo fuente; la autenticacion
    # es de Windows (trusted connection) y se configura en .env si hace falta.
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL',
        'mssql+pyodbc://@localhost\\SQLEXPRESS/TheTechHouse'
        '?driver=ODBC+Driver+18+for+SQL+Server&TrustServerCertificate=yes')

    SQLALCHEMY_TRACK_MODIFICATIONS = False
