import os

# Configuración del servidor
bind = f"0.0.0.0:{os.environ.get('PORT', '8000')}"
workers = int(os.environ.get('WORKERS', '4'))
worker_class = "sync"
worker_connections = 1000
timeout = 30
keepalive = 2

# Configuración de logging
accesslog = "-"
errorlog = "-"
loglevel = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s"'

# Configuración de proceso
preload_app = True
max_requests = 1000
max_requests_jitter = 50

# Configuración de seguridad
limit_request_line = 4094
limit_request_fields = 100
limit_request_field_size = 8190