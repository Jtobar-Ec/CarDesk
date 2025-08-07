# CarDesk - Sistema de Inventario

Sistema de gestión de inventario para conservatorios musicales desarrollado con Flask y MySQL.

## 🚀 Características

- **Gestión de Inventario**: Artículos e instrumentos musicales
- **Control de Personal**: Registro y asignaciones
- **Proveedores**: Gestión de entradas y facturas
- **Reportes**: Análisis de stock y movimientos
- **Autenticación**: Sistema seguro de usuarios
- **Backups**: Respaldos automáticos locales y en la nube

## 📋 Requisitos

- Python 3.8+
- MySQL 5.7+
- pip (gestor de paquetes Python)

## ⚙️ Instalación

1. **Clonar repositorio**
```bash
git clone https://github.com/Jtobar-Ec/CarDesk.git
cd CarDesk
```

2. **Crear entorno virtual**
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows
```

3. **Instalar dependencias**
```bash
pip install -r requirements.txt
```

4. **Configurar MySQL**
```sql
CREATE DATABASE sistema_inventario;
CREATE USER 'flaskuser'@'localhost' IDENTIFIED BY 'flaskpass';
GRANT ALL PRIVILEGES ON sistema_inventario.* TO 'flaskuser'@'localhost';
FLUSH PRIVILEGES;
```

5. **Permisos adicionales para migración** (Requerido para funcionalidad de migración)
```bash
sudo mysql -u root
```
```sql
GRANT PROCESS, SELECT, SHOW VIEW, RELOAD ON *.* TO 'flaskuser'@'localhost';
FLUSH PRIVILEGES;
GRANT EXECUTE ON *.* TO 'flaskuser'@'localhost';
FLUSH PRIVILEGES;
```

6. **Configurar variables de entorno**
Editar `.env`:
```env
SECRET_KEY=tu-clave-secreta-aqui
MYSQL_USER=flaskuser
MYSQL_PASSWORD=flaskpass
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_DATABASE=sistema_inventario
```

7. **Crear tablas**
```bash
python -c "from app import create_app; from app.database import db; app = create_app(); app.app_context().push(); db.create_all()"
```

## 🏃‍♂️ Ejecutar

### Desarrollo
```bash
python run.py
```
Acceder a: http://localhost:5000

### Producción
```bash
./deploy.sh
```
Acceder a: http://localhost:8000

## 🖥️ Accesos Directos del Menú

Para facilitar el uso, puedes crear accesos directos en el menú del sistema:

### Crear accesos directos
```bash
# Hacer ejecutables los archivos .desktop
chmod +x CarDesk-Deploy.desktop CarDesk-Stop.desktop

# Copiar al menú de aplicaciones
cp CarDesk-Deploy.desktop ~/.local/share/applications/
cp CarDesk-Stop.desktop ~/.local/share/applications/

# Actualizar base de datos del menú
update-desktop-database ~/.local/share/applications/
```

### Usar desde el menú
1. **Menú de aplicaciones** → Buscar "CarDesk"
2. **"CarDesk - Producción"** → Iniciar servidor
3. **"CarDesk - Detener"** → Parar servidor

### Scripts disponibles
- `./deploy.sh` - Iniciar en producción
- `./stop.sh` - Detener servidor
- `python run.py` - Modo desarrollo

## 📁 Estructura

```
CarDesk/
├── app/
│   ├── database/         # Modelos y repositorios
│   ├── routes/          # Rutas web
│   ├── services/        # Lógica de negocio
│   ├── templates/       # Plantillas HTML
│   └── utils/          # Utilidades
├── backups/            # Respaldos
├── config/            # Configuraciones
└── requirements.txt   # Dependencias
```

## 🔧 Tecnologías

- **Backend**: Flask, SQLAlchemy, Flask-Login
- **Base de datos**: MySQL
- **Frontend**: Bootstrap, jQuery
- **Otros**: PyMySQL, python-dotenv

## 📝 Licencia

UPS License - ver archivo LICENSE para detalles.

## 👥 Contribuir

1. Fork del proyecto
2. Crear rama feature (`git checkout -b feature/nueva-funcionalidad`)
3. Commit cambios (`git commit -m 'Agregar funcionalidad'`)
4. Push a la rama (`git push origin feature/nueva-funcionalidad`)
5. Abrir Pull Request

## 📞 Soporte

Para reportar bugs o solicitar funcionalidades, crear un issue en GitHub.
