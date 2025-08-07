# 🚀 Guía de Despliegue para Producción

## Configuración Rápida

### 1. Configurar Variables de Entorno
```bash
cp .env.example .env
# Editar .env con tus valores reales
```

### 2. Desplegar en Producción
```bash
./deploy.sh
```

## Configuraciones por Entorno

### Desarrollo
```bash
python run.py
```

### Producción
```bash
export FLASK_ENV=production
gunicorn --config gunicorn.conf.py "app:create_app()"
```

## Variables de Entorno Críticas

- `FLASK_ENV`: `production` para producción
- `SECRET_KEY`: Clave secreta única y segura
- `MYSQL_*`: Configuración de base de datos
- `PORT`: Puerto del servidor (default: 8000)
- `WORKERS`: Número de workers de Gunicorn (default: 4)

## Diferencias Desarrollo vs Producción

| Característica | Desarrollo | Producción |
|----------------|------------|------------|
| Debug | ✅ Activado | ❌ Desactivado |
| Cookies Seguras | ❌ No | ✅ Sí |
| Pool DB | Básico | Optimizado |
| Servidor | Flask dev | Gunicorn |
| Logging | DEBUG | INFO/WARNING |

## Comandos Útiles

```bash
# Verificar configuración
python -c "from app import create_app; print(create_app('production').config)"

# Ejecutar en producción manualmente
FLASK_ENV=production gunicorn --config gunicorn.conf.py "app:create_app()"