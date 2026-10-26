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

    # Base de datos: NUNCA se escribe la contrasena en el codigo fuente.
    # Se define en .env, por ejemplo:
    #   DATABASE_URL=mysql+pymysql://root:tu_password@localhost/the_tech_house
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL', 'mysql+pymysql://root@localhost/the_tech_house')

    SQLALCHEMY_TRACK_MODIFICATIONS = False
