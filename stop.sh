#!/bin/bash

echo "🛑 Deteniendo servidor CarDesk..."

# Buscar y matar procesos de Gunicorn
if pgrep -f "gunicorn.*app:create_app" > /dev/null; then
    pkill -f "gunicorn.*app:create_app"
    echo "✅ Servidor detenido exitosamente"
    echo "📊 Procesos eliminados:"
    echo "   - Gunicorn master process"
    echo "   - Workers (4 procesos)"
else
    echo "ℹ️  No hay servidor CarDesk ejecutándose"
fi

echo ""
echo "🔍 Estado actual:"
if pgrep -f "gunicorn.*app:create_app" > /dev/null; then
    echo "❌ Aún hay procesos activos"
else
    echo "✅ Servidor completamente detenido"
fi

read -p "Presiona Enter para cerrar..."