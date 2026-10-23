import os

class Config:
    # Clave secreta para sesiones
    SECRET_KEY = os.environ.get('SECRET_KEY', 'the_tech_house_secret_key_2026')

    # Cambia estos datos por los de tu MySQL
    SQLALCHEMY_DATABASE_URI = "mysql+pymysql://root:12345@localhost/the_tech_house"

    SQLALCHEMY_TRACK_MODIFICATIONS = False