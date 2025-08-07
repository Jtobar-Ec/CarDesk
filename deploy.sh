#!/bin/bash

# Cambiar al directorio del proyecto
cd "$(dirname "$0")"

# Script de despliegue para producción
echo "🚀 Iniciando despliegue en producción..."
echo "📁 Directorio: $(pwd)"

# Activar entorno virtual si existe
if [ -d "venv" ]; then
    echo "🔧 Activando entorno virtual..."
    source venv/bin/activate
fi

# Verificar que existe el archivo .env
if [ ! -f .env ]; then
    echo "❌ Error: Archivo .env no encontrado. Copia .env.example a .env y configúralo."
    read -p "Presiona Enter para cerrar..."
    exit 1
fi

# Instalar dependencias
echo "📦 Instalando dependencias..."
pip install -r requirements.txt

# Configurar variable de entorno para producción
export FLASK_ENV=production

# Ejecutar con Gunicorn
echo "🔥 Iniciando servidor con Gunicorn..."
echo "🌐 Accede en: http://localhost:8000"
gunicorn --config gunicorn.conf.py "app:create_app()"