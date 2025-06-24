from flask import Flask
from flask_login import LoginManager
from .database import db, init_app

def create_app():
    app = Flask(__name__)
    
    # Configuración básica de la base de datos
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///conservatorio.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = 'dev-key-segura'  # Para flash messages
    
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
        
    return app