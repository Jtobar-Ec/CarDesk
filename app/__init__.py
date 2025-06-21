from flask import Flask

def create_app():
    app = Flask(__name__)
    
    # Ruta de prueba
    @app.route('/test')
    def test_route():
        return "¡Backend funcionando correctamente!", 200
        
    return app