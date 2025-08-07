import os
from app import create_app
from app.database import db

# Crear app con configuración basada en entorno
config_name = os.environ.get('FLASK_ENV', 'development')
app = create_app(config_name)

if __name__ == '__main__':
    if config_name == 'production':
        print("❌ Para producción usa: ./deploy.sh o gunicorn --config gunicorn.conf.py 'app:create_app()'")
    else:
        print("🔧 Iniciando servidor Flask en modo desarrollo...")
        print("📍 Accede a la aplicación en: http://localhost:5000")
        app.run(debug=True, host='0.0.0.0', port=5000)