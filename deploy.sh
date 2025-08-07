#!/bin/bash

# Script de despliegue para producción
echo "🚀 Iniciando despliegue en producción..."

# Verificar que existe el archivo .env
if [ ! -f .env ]; then
    echo "❌ Error: Archivo .env no encontrado. Copia .env.example a .env y configúralo."
    exit 1
fi

# Instalar dependencias
echo "📦 Instalando dependencias..."
pip install -r requirements.txt

# Configurar variable de entorno para producción
export FLASK_ENV=production

# Ejecutar con Gunicorn
echo "🔥 Iniciando servidor con Gunicorn..."
gunicorn --config gunicorn.conf.py "app:create_app()"