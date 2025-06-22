from flask import Flask
from .database import db, init_app

def create_app():
    app = Flask(__name__)
    
    # Configuración básica de la base de datos
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///conservatorio.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = 'dev-key-segura'  # Para flash messages
    
    # Inicializar la base de datos
    init_app(app)
    
    # Importar rutas después de inicializar la base de datos
    from .routes.web import dashboard, instrumentos, articulos, proveedores
    
    # Ruta de prueba
    @app.route('/test')
    def test_route():
        return "¡Backend funcionando correctamente!", 200
    
    # Registrar blueprints
    app.register_blueprint(dashboard.bp, url_prefix='/')
    app.register_blueprint(instrumentos.bp, url_prefix='/instrumentos')
    app.register_blueprint(articulos.bp, url_prefix='/articulos')
    app.register_blueprint(proveedores.bp, url_prefix='/proveedores')
        
    return app