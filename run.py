from app import create_app
from app.database import db

app = create_app()

if __name__ == '__main__':
    with app.app_context():
        # Crear las tablas si no existen
        db.create_all()
        print("Base de datos inicializada correctamente")
    
    print("Iniciando servidor Flask...")
    print("Accede a la aplicación en: http://localhost:5000")
    app.run(debug=True, host='0.0.0.0', port=5000)