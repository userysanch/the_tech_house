from flask import Flask, redirect, render_template, url_for, request
from werkzeug.exceptions import HTTPException
from config import Config
from extensions import db, login_manager

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    login_manager.init_app(app)

    # Importar modelos
    from models import Usuario, Producto, Entrada, Venta, DetalleVenta

    @login_manager.user_loader
    def load_user(user_id):
        return Usuario.query.get(int(user_id))

    @login_manager.unauthorized_handler
    def unauthorized():
        return redirect(url_for('auth.login', next=request.url))

    # --- REGISTRO DE BLUEPRINTS ---
    from routes.auth import auth_bp
    from routes.main import main_bp
    from routes.entrada import entrada_bp
    from routes.inventario import inventario_bp
    from routes.caja import caja_bp
    from routes.ventas import ventas_bp
    from routes.reporte import reporte_bp
    from routes.buscador import buscador_bp
    from routes.scanner import scanner_bp
    from routes.registros import registros_bp
    from routes.exportar import exportar_bp
    from routes.api import api_bp
    from routes.catalogos import catalogos_bp
    from routes.kardex import kardex_bp
    from routes.devoluciones import devoluciones_bp
    from routes.usuarios import usuarios_bp
    from routes.promociones import promociones_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(entrada_bp, url_prefix='/entrada')
    app.register_blueprint(inventario_bp, url_prefix='/inventario')
    app.register_blueprint(caja_bp, url_prefix='/caja')
    app.register_blueprint(ventas_bp, url_prefix='/ventas')
    app.register_blueprint(reporte_bp, url_prefix='/reporte')
    app.register_blueprint(buscador_bp, url_prefix='/buscador')
    app.register_blueprint(scanner_bp, url_prefix='/scanner')
    app.register_blueprint(registros_bp, url_prefix='/registros')
    app.register_blueprint(exportar_bp, url_prefix='/exportar')
    app.register_blueprint(api_bp)
    app.register_blueprint(catalogos_bp, url_prefix='/catalogos')
    app.register_blueprint(kardex_bp, url_prefix='/kardex')
    app.register_blueprint(devoluciones_bp, url_prefix='/devoluciones')
    app.register_blueprint(usuarios_bp, url_prefix='/usuarios')
    app.register_blueprint(promociones_bp, url_prefix='/promociones')

    # Una excepcion no controlada debe dar una pagina chica y legible, no la
    # consola de depuracion de 83 KB que ngrok no puede entregar (se ve como
    # ERR_NGROK_3004 en el navegador).
    @app.errorhandler(Exception)
    def _error_no_controlado(e):
        if isinstance(e, HTTPException):
            return e  # 404, 405 y demas conservan su comportamiento normal
        app.logger.exception('Error no controlado en %s %s',
                             request.method, request.path)
        return render_template('error_500.html'), 500

    return app

def crear_usuarios_defecto():
    """Crea usuarios por defecto si no existen."""
    from models import Usuario

    usuarios = [
        ('admin', 'admin123', 'Administrador', 'admin'),
        ('vendedor', 'vendedor123', 'Vendedor', 'empleado'),
    ]

    for username, password, nombre, rol in usuarios:
        if not Usuario.query.filter_by(username=username).first():
            u = Usuario(username=username, nombre=nombre, rol=rol)
            u.set_password(password)
            db.session.add(u)

    db.session.commit()

if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        db.create_all()
        crear_usuarios_defecto()
    import os
    ssl_cert = os.path.join(os.path.dirname(os.path.abspath(__file__)), '192.168.0.11+1.pem')
    ssl_key = os.path.join(os.path.dirname(os.path.abspath(__file__)), '192.168.0.11+1-key.pem')
    app.run(debug=True, host='0.0.0.0', port=5000, ssl_context=(ssl_cert, ssl_key))

