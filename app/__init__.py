from flask import Flask
from flask_login import LoginManager
from .database import db, init_app
from .config import Config

def create_app(config_name='development'):
    app = Flask(__name__)
    
    # Cargar configuración completa desde config.py
    app.config.from_object(Config)
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB máximo para uploads
    
    # Inicializar la base de datos
    init_app(app)
    
    # Configurar Flask-Login
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Debes iniciar sesión para acceder a esta página.'
    login_manager.login_message_category = 'info'
    
    @login_manager.user_loader
    def load_user(user_id):
        from .database.models import Usuario
        return Usuario.query.get(int(user_id))
    
    # Importar rutas después de inicializar la base de datos
    try:
        from .routes.web import dashboard, instrumentos, articulos, proveedores, movimientos, auth, reportes, migracion, personal, backups
        
        # Ruta de prueba
        @app.route('/test')
        def test_route():
            return "¡Backend funcionando correctamente!", 200
        
        # Registrar blueprints
        app.register_blueprint(auth.bp, url_prefix='/auth')
        app.register_blueprint(dashboard.bp, url_prefix='/')
        app.register_blueprint(instrumentos.bp, url_prefix='/instrumentos')
        app.register_blueprint(articulos.bp, url_prefix='/articulos')
        app.register_blueprint(proveedores.bp, url_prefix='/proveedores')
        app.register_blueprint(movimientos.bp, url_prefix='/movimientos')
        app.register_blueprint(reportes.bp, url_prefix='/reportes')
        app.register_blueprint(migracion.bp, url_prefix='/migracion')
        app.register_blueprint(personal.bp, url_prefix='/personal')
        app.register_blueprint(backups.bp, url_prefix='/backups')
        
        
    except ImportError as import_error:
        error_message = str(import_error)
        print(f"Error importando blueprints: {error_message}")
        # Crear ruta de error temporal
        @app.route('/')
        def error_route():
            return f"Error de configuración: {error_message}", 500
    
    # Manejo de errores
    @app.errorhandler(404)
    def not_found_error(error):
        return "Página no encontrada", 404
    
    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return "Error interno del servidor", 500
        
    return app