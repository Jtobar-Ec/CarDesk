from flask import Blueprint, render_template, request, jsonify, make_response, flash, redirect, url_for, send_file
from flask_login import login_required, current_user
from datetime import datetime
import os
import shutil
import tempfile
import zipfile
from werkzeug.utils import secure_filename
from app.database import db
from app.database.models import MovimientoDetalle, Item, Articulo, Instrumento, Proveedor, Persona, Consumo, Entrada, Usuario
from app.services.import_service import ImportService
from sqlalchemy import text
import subprocess

bp = Blueprint('migracion', __name__)

# Configuración
UPLOAD_FOLDER = 'temp_uploads'
ALLOWED_EXTENSIONS = {'zip', 'sql'} # Eliminado 'db'

def allowed_file(filename):
    """Verifica que el archivo tenga una extensión permitida"""
    if '.' not in filename:
        return False
    ext = filename.rsplit('.', 1)[1].lower()
    return ext in ALLOWED_EXTENSIONS

@bp.route('/')
@login_required
def index():
    """Página principal de migración y backup"""
    return render_template('migracion/index.html')

@bp.route('/exportar-completa', methods=['POST'])
@login_required
def exportar_base_completa():
    """Exportar toda la base de datos desde MySQL"""
    try:
        # Credenciales y nombre de la base de datos
        db_user = 'flaskuser'
        db_password = 'flaskpass'
        db_name = 'sistema_inventario'
        
        # Crear archivo temporal para el volcado
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.sql')

        # Usar mysqldump para exportar la base de datos
        mysqldump_command = f"mysqldump -u {db_user} -p{db_password} {db_name} > {temp_file.name}"

        # Ejecutar el comando mysqldump
        subprocess.run(mysqldump_command, shell=True, check=True)
        
        # Crear respuesta con el archivo de volcado
        response = make_response(send_file(
            temp_file.name,
            as_attachment=True,
            download_name=f'{db_name}_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.sql',
            mimetype='application/sql'
        ))

        # Limpiar archivo temporal después de enviar
        @response.call_on_close
        def cleanup():
            try:
                os.unlink(temp_file.name)
            except:
                pass
        
        return response
        
    except Exception as e:
        return jsonify({'error': f'Error al exportar: {str(e)}'}), 500


import subprocess
import os

def _procesar_importacion_sql(file_path):
    """Procesar la importación de un archivo .sql usando el servicio de importación"""
    try:
        import_service = ImportService()
        return import_service.import_sql_file(file_path)
    except Exception as e:
        return {
            'success': False,
            'message': f"Error al procesar importación SQL: {str(e)}"
        }

@bp.route('/importar', methods=['POST'])
@login_required
def importar_base():
    """Importar base de datos desde archivo .db o .zip a MySQL"""
    try:
        if 'archivo' not in request.files:
            flash('No se seleccionó ningún archivo', 'error')
            return redirect(url_for('migracion.index'))
        
        file = request.files['archivo']
        if file.filename == '':
            flash('No se seleccionó ningún archivo', 'error')
            return redirect(url_for('migracion.index'))
        
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            
            # Mostrar el archivo y su extensión para depuración
            print(f"Archivo recibido: {filename}, extensión: {filename.rsplit('.', 1)[1].lower()}")
            
            # Crear directorio temporal si no existe
            os.makedirs(UPLOAD_FOLDER, exist_ok=True)
            
            # Guardar archivo temporalmente
            temp_path = os.path.join(UPLOAD_FOLDER, filename)
            file.save(temp_path)
            
            # Verificar la extensión y procesar el archivo adecuado
            if filename.endswith('.zip'):
                resultado = _procesar_importacion_zip(temp_path)
            elif filename.endswith('.sql'):
                resultado = _procesar_importacion_sql(temp_path)  # Si es SQL
            else:
                resultado = {'success': False, 'message': 'Formato de archivo no soportado'}
            
            # Limpiar archivo temporal
            try:
                os.remove(temp_path)
            except:
                pass
            
            # Mostrar resultado
            if resultado['success']:
                flash(resultado['message'], 'success')
            else:
                flash(resultado['message'], 'error')
        else:
            flash('Tipo de archivo no permitido', 'error')
        
        return redirect(url_for('migracion.index'))
        
    except Exception as e:
        flash(f'Error al importar: {str(e)}', 'error')
        return redirect(url_for('migracion.index'))

def _procesar_importacion_zip(file_path):
    """Procesar la importación de un archivo .zip usando el servicio de importación"""
    try:
        import_service = ImportService()
        return import_service.import_zip_file(file_path)
    except Exception as e:
        return {
            'success': False,
            'message': f"Error al procesar archivo ZIP: {str(e)}"
        }
    

@bp.route('/validar-archivo', methods=['POST'])
@login_required
def validar_archivo():
    """Validar archivo antes de importar a MySQL usando el servicio de importación"""
    try:
        if 'archivo' not in request.files:
            return jsonify({'valid': False, 'message': 'No se seleccionó archivo'})
        
        file = request.files['archivo']
        if file.filename == '':
            return jsonify({'valid': False, 'message': 'No se seleccionó archivo'})
        
        if not allowed_file(file.filename):
            return jsonify({'valid': False, 'message': 'Tipo de archivo no permitido. Solo se permiten archivos .sql y .zip'})
        
        filename = secure_filename(file.filename)
        
        # Validar tamaño del archivo (máximo 100MB)
        file.seek(0, 2)
        file_size = file.tell()
        file.seek(0)
        
        max_size = 100 * 1024 * 1024  # 100MB
        if file_size > max_size:
            return jsonify({
                'valid': False,
                'message': f'El archivo es demasiado grande ({file_size / (1024*1024):.1f}MB). Máximo permitido: 100MB'
            })
        
        if file_size == 0:
            return jsonify({'valid': False, 'message': 'El archivo está vacío'})
        
        # Guardar archivo temporalmente para validación
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)
        temp_path = os.path.join(UPLOAD_FOLDER, f"temp_validation_{filename}")
        file.save(temp_path)
        
        try:
            import_service = ImportService()
            
            if filename.endswith('.sql'):
                # Validar archivo SQL directamente
                validation = import_service.validate_sql_file(temp_path)
                
                if validation['valid']:
                    return jsonify({
                        'valid': True,
                        'message': 'Archivo SQL válido',
                        'info': f'Tamaño: {file_size / (1024*1024):.2f}MB - Dump de MySQL detectado'
                    })
                else:
                    return jsonify({
                        'valid': False,
                        'message': validation['message']
                    })
                    
            elif filename.endswith('.zip'):
                # Validar archivo ZIP
                try:
                    if not zipfile.is_zipfile(temp_path):
                        return jsonify({'valid': False, 'message': 'El archivo ZIP está corrupto'})
                    
                    with zipfile.ZipFile(temp_path, 'r') as zip_ref:
                        file_list = zip_ref.namelist()
                        sql_files = [f for f in file_list if f.endswith('.sql')]
                        
                        if not sql_files:
                            return jsonify({
                                'valid': False,
                                'message': 'El archivo ZIP no contiene archivos .sql'
                            })
                        
                        # Extraer y validar el primer archivo SQL
                        with tempfile.TemporaryDirectory() as temp_dir:
                            zip_ref.extractall(temp_dir)
                            sql_file_path = os.path.join(temp_dir, sql_files[0])
                            
                            validation = import_service.validate_sql_file(sql_file_path)
                            
                            if validation['valid']:
                                return jsonify({
                                    'valid': True,
                                    'message': 'Archivo ZIP válido',
                                    'info': f'Tamaño: {file_size / (1024*1024):.2f}MB - Contiene {len(sql_files)} archivo(s) SQL válido(s)'
                                })
                            else:
                                return jsonify({
                                    'valid': False,
                                    'message': f'El archivo SQL dentro del ZIP no es válido: {validation["message"]}'
                                })
                                
                except zipfile.BadZipFile:
                    return jsonify({'valid': False, 'message': 'El archivo ZIP está corrupto'})
                except Exception as e:
                    return jsonify({'valid': False, 'message': f'Error al validar ZIP: {str(e)}'})
            
            return jsonify({'valid': True, 'message': 'Archivo válido'})
            
        finally:
            # Limpiar archivo temporal
            try:
                os.remove(temp_path)
            except:
                pass
        
    except Exception as e:
        return jsonify({'valid': False, 'message': f'Error al validar archivo: {str(e)}'})



@bp.route('/estado-bd', methods=['GET'])
@login_required
def estado_base_datos():
    """Obtener estado actual de la base de datos"""
    try:
        import_service = ImportService()
        status = import_service.get_import_status()
        return jsonify(status)
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
        import_service = ImportService()
        db_config = import_service.get_db_config()
        
        # Comando simple para probar conexión
        test_command = [
            'mysql',
            f'-h{db_config["host"]}',
            f'-P{db_config["port"]}',
            f'-u{db_config["user"]}',
            f'-p{db_config["password"]}',
            '-e', 'SELECT 1;',
            db_config['database']
        ]
        
        result = subprocess.run(
            test_command,
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            return jsonify({
                'success': True,
                'message': 'Conexión exitosa con la base de datos',
                'database': db_config['database'],
                'host': db_config['host']
            })
        else:
            return jsonify({
                'success': False,
                'message': f'Error de conexión: {result.stderr}'
            }), 500
            
    except subprocess.TimeoutExpired:
        return jsonify({
            'success': False,
            'message': 'Timeout al conectar con la base de datos'
        }), 500
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error probando conexión: {str(e)}'
        }), 500
