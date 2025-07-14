import subprocess
import os
import tempfile
import shutil
from flask import Blueprint, render_template, request, jsonify, make_response, flash, redirect, url_for, send_file, current_app
from flask_login import login_required
from datetime import datetime
from werkzeug.utils import secure_filename
import mysql.connector
from mysql.connector import Error
import logging

bp = Blueprint('migracion', __name__)

# Configuración
UPLOAD_FOLDER = 'temp_uploads'
ALLOWED_EXTENSIONS = {'sql'}
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB

def get_db_config():
    """Obtener configuración de la base de datos desde las variables de entorno o configuración"""
    return {
        'host': os.getenv('DB_HOST', 'localhost'),
        'port': int(os.getenv('DB_PORT', 3306)),
        'user': os.getenv('DB_USER', 'flaskuser'),
        'password': os.getenv('DB_PASSWORD', 'flaskpass'),
        'database': os.getenv('DB_NAME', 'sistema_inventario')
    }
def test_db_connection():
    """Probar conexión a la base de datos"""
    logging.debug("Probando conexión a la base de datos.")
    try:
        db_config = get_db_config()
        connection = mysql.connector.connect(**db_config)
        if connection.is_connected():
            cursor = connection.cursor()
            cursor.execute("SELECT VERSION()")
            version = cursor.fetchone()
            cursor.close()
            connection.close()
            logging.debug(f"Conexión exitosa - MySQL {version[0]}")
            return True, f"Conexión exitosa - MySQL {version[0]}"
    except Error as e:
        logging.error(f"Error de conexión: {str(e)}")
        return False, f"Error de conexión: {str(e)}"
    except Exception as e:
        logging.error(f"Error inesperado: {str(e)}")
        return False, f"Error inesperado: {str(e)}"
    
def get_database_info():
    """Obtener información de la base de datos"""
    logging.debug("Obteniendo información de la base de datos.")
    try:
        db_config = get_db_config()
        connection = mysql.connector.connect(**db_config)
        if connection.is_connected():
            cursor = connection.cursor()
            cursor.execute("SHOW TABLES")
            tables = [table[0] for table in cursor.fetchall()]
            cursor.execute("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = %s", (db_config['database'],))
            table_count = cursor.fetchone()[0]
            cursor.close()
            connection.close()
            logging.debug(f"Tablas obtenidas: {tables}")
            return {
                'success': True,
                'database': db_config['database'],
                'host': db_config['host'],
                'port': db_config['port'],
                'tables': tables,
                'tables_count': table_count
            }
    except Error as e:
        logging.error(f"Error de base de datos: {str(e)}")
        return {
            'success': False,
            'message': f"Error de base de datos: {str(e)}"
        }
    except Exception as e:
        logging.error(f"Error inesperado: {str(e)}")
        return {
            'success': False,
            'message': f"Error inesperado: {str(e)}"
        }

def allowed_file(filename):
    """Verifica que el archivo tenga una extensión permitida"""
    logging.debug(f"Verificando si el archivo tiene una extensión permitida: {filename}")
    if '.' not in filename:
        return False
    ext = filename.rsplit('.', 1)[1].lower()
    return ext in ALLOWED_EXTENSIONS

def validate_sql_file(file_path):
    """Validar que el archivo SQL sea válido"""
    logging.debug(f"Validando el archivo SQL: {file_path}")
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read(1000)  # Leer primeros 1000 caracteres
            
            # Verificar que contiene comandos SQL básicos
            sql_keywords = ['CREATE', 'INSERT', 'UPDATE', 'ALTER', 'DROP']
            if not any(keyword in content.upper() for keyword in sql_keywords):
                logging.error("El archivo no parece contener comandos SQL válidos.")
                return False, "El archivo no parece contener comandos SQL válidos"
            
            logging.debug("Archivo SQL válido.")
            return True, "Archivo SQL válido"
    except UnicodeDecodeError:
        logging.error("El archivo no puede ser leído como texto UTF-8")
        return False, "El archivo no puede ser leído como texto UTF-8"
    except Exception as e:
        logging.error(f"Error al validar archivo: {str(e)}")
        return False, f"Error al validar archivo: {str(e)}"

@bp.route('/')
@login_required
def index():
    """Página principal de migración"""
    return render_template('migracion/index.html')

@bp.route('/exportar-completa', methods=['POST'])
@login_required
def exportar_base_completa():
    """Exportar toda la base de datos desde MySQL"""
    try:
        logging.debug("Iniciando exportación completa de la base de datos.")
        db_config = get_db_config()
        
        # Crear directorio temporal si no existe
        temp_dir = tempfile.mkdtemp()
        filename = f'{db_config["database"]}_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.sql'
        temp_file_path = os.path.join(temp_dir, filename)
        
        # Construir comando mysqldump
        mysqldump_command = [
            'mysqldump',
            f'-h{db_config["host"]}',
            f'-P{db_config["port"]}',
            f'-u{db_config["user"]}',
            f'-p{db_config["password"]}',
            '--routines',
            '--triggers',
            '--single-transaction',
            '--quick',
            '--lock-tables=false',
            db_config['database']
        ]
        logging.debug(f"Comando mysqldump: {' '.join(mysqldump_command)}")
        
        # Ejecutar mysqldump
        with open(temp_file_path, 'w') as output_file:
            result = subprocess.run(
                mysqldump_command,
                stdout=output_file,
                stderr=subprocess.PIPE,
                text=True,
                timeout=300  # 5 minutos timeout
            )
        
        if result.returncode != 0:
            logging.error(f"Error en mysqldump: {result.stderr}")
            shutil.rmtree(temp_dir)
            return jsonify({
                'error': f'Error en mysqldump: {result.stderr}'
            }), 500
        
        # Verificar que el archivo se creó correctamente
        if not os.path.exists(temp_file_path) or os.path.getsize(temp_file_path) == 0:
            logging.error("El archivo de exportación está vacío o no se pudo crear")
            shutil.rmtree(temp_dir)
            return jsonify({
                'error': 'El archivo de exportación está vacío o no se pudo crear'
            }), 500
        
        # Preparar respuesta con descarga del archivo
        logging.debug(f"Archivo de exportación creado: {temp_file_path}")
        response = make_response(send_file(
            temp_file_path,
            as_attachment=True,
            download_name=filename,
            mimetype='application/sql'
        ))

        # Limpiar archivos temporales después de enviar
        @response.call_on_close
        def cleanup():
            try:
                shutil.rmtree(temp_dir)
                logging.debug(f"Archivos temporales eliminados.")
            except Exception as e:
                logging.error(f'Error al limpiar archivos temporales: {e}')

        return response
        
    except subprocess.TimeoutExpired:
        logging.error("Timeout en la exportación.")
        return jsonify({'error': 'Timeout en la exportación - la operación tardó demasiado'}), 500
    except Exception as e:
        logging.error(f"Error al exportar: {str(e)}")
        return jsonify({'error': f'Error al exportar: {str(e)}'}), 500

@bp.route('/importar', methods=['POST'])
def importar_base():
    """Importar base de datos desde archivo .sql"""
    try:
        logging.debug("Iniciando importación de base de datos.")
        if 'archivo' not in request.files:
            flash('No se seleccionó ningún archivo', 'error')
            return redirect(url_for('migracion.index'))

        file = request.files['archivo']
        if file.filename == '':
            flash('No se seleccionó ningún archivo', 'error')
            return redirect(url_for('migracion.index'))

        if not file or not allowed_file(file.filename):
            flash('Tipo de archivo no permitido. Solo se permiten archivos .sql', 'error')
            return redirect(url_for('migracion.index'))

        # Verificar tamaño del archivo
        file.seek(0, 2)  # Ir al final del archivo
        file_size = file.tell()
        file.seek(0)  # Volver al inicio

        if file_size > MAX_FILE_SIZE:
            flash(f'El archivo es demasiado grande ({file_size / (1024 * 1024):.1f}MB). Máximo permitido: {MAX_FILE_SIZE / (1024 * 1024):.0f}MB', 'error')
            return redirect(url_for('migracion.index'))

        if file_size == 0:
            flash('El archivo está vacío', 'error')
            return redirect(url_for('migracion.index'))

        # Guardar archivo temporal
        filename = secure_filename(file.filename)
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)
        temp_path = os.path.join(UPLOAD_FOLDER, f"import_{filename}")
        file.save(temp_path)

        if not os.path.exists(temp_path):
            flash('El archivo no se pudo guardar correctamente', 'error')
            return redirect(url_for('migracion.index'))

        logging.debug(f"Archivo guardado temporalmente en: {temp_path}")

        # Llamar a la función para importar la base de datos
        success, message = importar_bd(temp_path)

        # Limpiar archivo temporal
        try:
            os.remove(temp_path)
        except Exception as e:
            flash(f'Error al eliminar archivo temporal: {str(e)}', 'warning')

        if success:
            flash('Base de datos importada exitosamente', 'success')
        else:
            flash(f'Error al importar la base de datos: {message}', 'error')

        # Redirigir después de la importación
        logging.debug("Redirigiendo después de la importación.")
        return redirect(url_for('migracion.index'))

    except Exception as e:
        flash(f'Error inesperado al importar: {str(e)}', 'error')
        return redirect(url_for('migracion.index'))

def importar_bd(file_path):
    """Importar la base de datos desde el archivo SQL"""
    try:
        logging.debug(f"Iniciando importación desde archivo: {file_path}")
        
        db_user = 'flaskuser'
        db_password = 'flaskpass'
        db_name = 'sistema_inventario'

        # Usar el comando MySQL para importar el archivo
        import_command = f"mysql -u {db_user} -p{db_password} {db_name} < {file_path}"
        logging.debug(f"Ejecutando comando de importación: {import_command}")
        
        result = subprocess.run(import_command, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        if result.returncode == 0:
            logging.debug("Importación exitosa.")
            return True, "Importación exitosa"
        else:
            logging.error(f"Error en MySQL: {result.stderr}")
            return False, f"Error en MySQL: {result.stderr}"

    except subprocess.CalledProcessError as e:
        logging.error(f"Error al ejecutar el comando MySQL: {e.stderr}")
        return False, f"Error al ejecutar el comando MySQL: {e.stderr}"
    except Exception as e:
        logging.error(f"Error inesperado: {str(e)}")
        return False, f"Error inesperado: {str(e)}"
    """Importar la base de datos desde el archivo SQL"""
    try:
        logging.debug(f"Iniciando importación desde archivo: {file_path}")
        
        db_user = 'flaskuser'
        db_password = 'flaskpass'
        db_name = 'sistema_inventario'

        # Usar el comando MySQL para importar el archivo
        import_command = f"mysql -u {db_user} -p{db_password} {db_name} < {file_path}"
        logging.debug(f"Ejecutando comando de importación: {import_command}")
        
        result = subprocess.run(import_command, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        if result.returncode == 0:
            logging.debug("Importación exitosa.")
            return True, "Importación exitosa"
        else:
            logging.error(f"Error en MySQL: {result.stderr}")
            return False, f"Error en MySQL: {result.stderr}"

    except subprocess.CalledProcessError as e:
        logging.error(f"Error al ejecutar el comando MySQL: {e.stderr}")
        return False, f"Error al ejecutar el comando MySQL: {e.stderr}"
    except Exception as e:
        logging.error(f"Error inesperado: {str(e)}")
        return False, f"Error inesperado: {str(e)}"

@bp.route('/validar-archivo', methods=['POST'])
@login_required
def validar_archivo():
    """Validar archivo antes de importar a MySQL"""
    try:
        if 'archivo' not in request.files:
            return jsonify({'valid': False, 'message': 'No se seleccionó archivo'})
            
        file = request.files['archivo']
        if file.filename == '':
            return jsonify({'valid': False, 'message': 'No se seleccionó archivo'})
            
        if not allowed_file(file.filename):
            return jsonify({'valid': False, 'message': 'Tipo de archivo no permitido. Solo se permiten archivos .sql'})

        filename = secure_filename(file.filename)
        file.seek(0, 2)
        file_size = file.tell()
        file.seek(0)

        if file_size > MAX_FILE_SIZE:
            return jsonify({
                'valid': False,
                'message': f'El archivo es demasiado grande ({file_size / (1024*1024):.1f}MB). Máximo permitido: {MAX_FILE_SIZE / (1024*1024):.0f}MB'
            })
            
        if file_size == 0:
            return jsonify({'valid': False, 'message': 'El archivo está vacío'})

        # Guardar archivo temporal para validación
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)
        temp_path = os.path.join(UPLOAD_FOLDER, f"validation_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{filename}")
        file.save(temp_path)

        try:
            # Validar contenido del archivo
            is_valid, message = validate_sql_file(temp_path)
            
            if is_valid:
                # Información adicional del archivo
                with open(temp_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    lines = content.count('\n')
                    
                return jsonify({
                    'valid': True,
                    'message': 'Archivo válido para importar',
                    'info': f'Tamaño: {file_size / (1024*1024):.1f}MB, Líneas: {lines}'
                })
            else:
                return jsonify({'valid': False, 'message': message})
                
        finally:
            # Limpiar archivo temporal
            try:
                os.remove(temp_path)
            except Exception as e:
                current_app.logger.warning(f'Error al eliminar archivo temporal de validación: {e}')

    except Exception as e:
        return jsonify({'valid': False, 'message': f'Error al validar archivo: {str(e)}'})

@bp.route('/estado-bd', methods=['GET'])
@login_required
def estado_base_datos():
    """Obtener estado actual de la base de datos"""
    try:
        db_info = get_database_info()
        return jsonify(db_info)
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error obteniendo estado: {str(e)}'
        }), 500

@bp.route('/test-conexion', methods=['GET'])
@login_required
def test_conexion_bd():
    """Probar conexión con la base de datos MySQL"""
    try:
        db_config = get_db_config()
        is_connected, message = test_db_connection()
        
        if is_connected:
            return jsonify({
                'success': True,
                'message': message,
                'database': db_config['database'],
                'host': db_config['host']
            })
        else:
            return jsonify({
                'success': False,
                'message': message
            }), 500
            
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error probando conexión: {str(e)}'
        }), 500

# Función para limpiar archivos temporales antiguos (opcional)
def cleanup_old_temp_files():
    """Limpiar archivos temporales antiguos"""
    try:
        if os.path.exists(UPLOAD_FOLDER):
            now = datetime.now()
            for filename in os.listdir(UPLOAD_FOLDER):
                file_path = os.path.join(UPLOAD_FOLDER, filename)
                if os.path.isfile(file_path):
                    file_time = datetime.fromtimestamp(os.path.getmtime(file_path))
                    if (now - file_time).total_seconds() > 3600:  # 1 hora
                        os.remove(file_path)
    except Exception as e:
        current_app.logger.warning(f'Error al limpiar archivos temporales: {e}')

# Ejecutar limpieza al cargar el módulo
cleanup_old_temp_files()
