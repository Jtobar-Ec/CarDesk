from flask import Blueprint, render_template, request, jsonify, make_response, flash, redirect, url_for, send_file
from flask_login import login_required, current_user
from datetime import datetime, date, timedelta
import os
import shutil
import sqlite3
import zipfile
import tempfile
import io
from werkzeug.utils import secure_filename
from app.database import db
from app.database.models import MovimientoDetalle, Item, Articulo, Instrumento, Proveedor, Persona, Consumo, Entrada, Usuario
from sqlalchemy import extract, text

bp = Blueprint('migracion', __name__)

# Configuración
UPLOAD_FOLDER = 'temp_uploads'
ALLOWED_EXTENSIONS = {'db', 'zip', 'sql'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@bp.route('/')
@login_required
def index():
    """Página principal de migración y backup"""
    return render_template('migracion/index.html')

@bp.route('/exportar-completa', methods=['POST'])
@login_required
def exportar_base_completa():
    """Exportar toda la base de datos"""
    try:
        # Ruta de la base de datos actual
        db_path = os.path.join('instance', 'conservatorio.db')
        
        if not os.path.exists(db_path):
            return jsonify({'error': 'Base de datos no encontrada'}), 404
        
        # Crear archivo temporal
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        
        # Copiar la base de datos
        shutil.copy2(db_path, temp_file.name)
        
        # Crear respuesta
        response = make_response(send_file(
            temp_file.name,
            as_attachment=True,
            download_name=f'conservatorio_backup_completo_{datetime.now().strftime("%Y%m%d_%H%M%S")}.db',
            mimetype='application/octet-stream'
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


@bp.route('/importar', methods=['POST'])
@login_required
def importar_base():
    """Importar base de datos"""
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
            
            # Crear directorio temporal si no existe
            os.makedirs(UPLOAD_FOLDER, exist_ok=True)
            
            # Guardar archivo temporalmente
            temp_path = os.path.join(UPLOAD_FOLDER, filename)
            file.save(temp_path)
            
            # Validar y procesar archivo
            if filename.endswith('.db'):
                resultado = _procesar_importacion_db(temp_path)
            elif filename.endswith('.zip'):
                resultado = _procesar_importacion_zip(temp_path)
            else:
                resultado = {'success': False, 'message': 'Formato de archivo no soportado'}
            
            # Limpiar archivo temporal
            try:
                os.remove(temp_path)
            except:
                pass
            
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

@bp.route('/validar-archivo', methods=['POST'])
@login_required
def validar_archivo():
    """Validar archivo antes de importar"""
    try:
        if 'archivo' not in request.files:
            return jsonify({'valid': False, 'message': 'No se seleccionó archivo'})
        
        file = request.files['archivo']
        if file.filename == '':
            return jsonify({'valid': False, 'message': 'No se seleccionó archivo'})
        
        if not allowed_file(file.filename):
            return jsonify({'valid': False, 'message': 'Tipo de archivo no permitido'})
        
        # Validaciones adicionales según el tipo de archivo
        filename = secure_filename(file.filename)
        
        if filename.endswith('.db'):
            # Validar que sea una base de datos SQLite válida
            temp_path = os.path.join(UPLOAD_FOLDER, 'temp_validation.db')
            os.makedirs(UPLOAD_FOLDER, exist_ok=True)
            file.save(temp_path)
            
            try:
                conn = sqlite3.connect(temp_path)
                cursor = conn.cursor()
                
                # Verificar que tenga las tablas esperadas
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
                tables = [row[0] for row in cursor.fetchall()]
                
                required_tables = ['tb_item', 'tb_articulo', 'tb_instrumento', 'tb_proveedores', 'tb_persona']
                missing_tables = [table for table in required_tables if table not in tables]
                
                conn.close()
                os.remove(temp_path)
                
                if missing_tables:
                    return jsonify({
                        'valid': False, 
                        'message': f'Base de datos incompleta. Faltan tablas: {", ".join(missing_tables)}'
                    })
                
                return jsonify({
                    'valid': True, 
                    'message': 'Archivo válido',
                    'info': f'Base de datos con {len(tables)} tablas encontradas'
                })
                
            except sqlite3.Error as e:
                try:
                    os.remove(temp_path)
                except:
                    pass
                return jsonify({'valid': False, 'message': f'Archivo de base de datos corrupto: {str(e)}'})
        
        return jsonify({'valid': True, 'message': 'Archivo válido'})
        
    except Exception as e:
        return jsonify({'valid': False, 'message': f'Error al validar: {str(e)}'})

def _procesar_importacion_db(file_path):
    """Procesar importación de archivo .db con sincronización completa"""
    try:
        import_conn = sqlite3.connect(file_path)
        import_cursor = import_conn.cursor()

        # Verificar estructura
        import_cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row[0] for row in import_cursor.fetchall()]

        required_tables = ['tb_item', 'tb_movimiento_detalle']
        if not all(table in tables for table in required_tables):
            import_conn.close()
            return {'success': False, 'message': 'Estructura de base de datos incompatible'}

        registros_importados = 0
        registros_eliminados = 0
        errores = []

        def importar_tabla(nombre_tabla):
            nonlocal registros_importados, registros_eliminados, errores

            if nombre_tabla not in tables:
                errores.append(f"Tabla {nombre_tabla} no encontrada en el archivo de importación")
                return

            try:
                # Obtener información de columnas y clave primaria
                import_cursor.execute(f"PRAGMA table_info({nombre_tabla})")
                columns_info = import_cursor.fetchall()
                column_names = [col[1] for col in columns_info]
                primary_key = [col[1] for col in columns_info if col[5] == 1][0]

                # 1. Obtener IDs de la base de datos importada
                import_cursor.execute(f"SELECT {primary_key} FROM {nombre_tabla}")
                ids_importados = {row[0] for row in import_cursor.fetchall()}

                # 2. Obtener IDs de la base de datos actual
                ids_actuales = {row[0] for row in 
                               db.session.execute(text(f"SELECT {primary_key} FROM {nombre_tabla}")).fetchall()}

                # 3. Identificar registros a eliminar
                ids_a_eliminar = ids_actuales - ids_importados

                # 4. Eliminar registros que no están en el archivo importado
                if ids_a_eliminar:
                    # Solución para el problema de la cláusula IN
                    ids_list = list(ids_a_eliminar)
                    if len(ids_list) == 1:
                        # Caso especial para un solo elemento
                        stmt = text(f"DELETE FROM {nombre_tabla} WHERE {primary_key} = :id")
                        db.session.execute(stmt, {'id': ids_list[0]})
                    else:
                        # Generar placeholders dinámicos
                        placeholders = ', '.join([f':id_{i}' for i in range(len(ids_list))])
                        params = {f'id_{i}': id_val for i, id_val in enumerate(ids_list)}
                        stmt = text(f"DELETE FROM {nombre_tabla} WHERE {primary_key} IN ({placeholders})")
                        db.session.execute(stmt, params)
                    
                    registros_eliminados += len(ids_a_eliminar)

                # 5. Importar/actualizar todos los registros del archivo importado
                import_cursor.execute(f"SELECT * FROM {nombre_tabla}")
                registros = import_cursor.fetchall()

                for registro in registros:
                    try:
                        registro_dict = dict(zip(column_names, registro))
                        
                        # Verificar si el registro ya existe
                        existing = db.session.execute(
                            text(f"SELECT 1 FROM {nombre_tabla} WHERE {primary_key} = :pk_val"),
                            {'pk_val': registro_dict[primary_key]}
                        ).fetchone()

                        if existing:
                            # Actualizar registro existente
                            set_clause = ', '.join([f"{col}=:{col}" for col in column_names])
                            stmt = text(f"UPDATE {nombre_tabla} SET {set_clause} WHERE {primary_key}=:{primary_key}")
                        else:
                            # Insertar nuevo registro
                            columns = ', '.join(column_names)
                            placeholders = ', '.join([f':{col}' for col in column_names])
                            stmt = text(f"INSERT INTO {nombre_tabla} ({columns}) VALUES ({placeholders})")

                        db.session.execute(stmt, registro_dict)
                        registros_importados += 1

                    except Exception as e:
                        errores.append(f"Error en {nombre_tabla} ID {registro[0]}: {str(e)}")
                        continue

                db.session.commit()

            except Exception as e:
                errores.append(f"Error procesando tabla {nombre_tabla}: {str(e)}")
                db.session.rollback()

        try:
            db.session.rollback()
            db.session.execute(text("PRAGMA foreign_keys=OFF"))

            # Orden de importación considerando dependencias
            tablas_orden = [
                'tb_proveedores',
                'tb_persona',
                'tb_item',
                'tb_articulo',
                'tb_instrumento',
                'tb_entrada',
                'tb_consumo',
                'tb_movimiento_detalle',
                'tb_stock'
            ]

            for tabla in tablas_orden:
                importar_tabla(tabla)

            db.session.execute(text("PRAGMA foreign_keys=ON"))
            db.session.commit()

            mensaje = (f"Sincronización completada. "
                      f"Registros importados/actualizados: {registros_importados}, "
                      f"Registros eliminados: {registros_eliminados}")
            
            if errores:
                mensaje += f" | Errores: {len(errores)}"
                if len(errores) <= 5:
                    mensaje += f" ({'; '.join(errores[:5])})"

            return {
                'success': len(errores) == 0 or registros_importados > 0,
                'message': mensaje,
                'imported': registros_importados,
                'deleted': registros_eliminados,
                'errors': len(errores)
            }

        except Exception as e:
            db.session.rollback()
            return {
                'success': False,
                'message': f'Error durante la sincronización: {str(e)}'
            }

        finally:
            import_conn.close()

    except Exception as e:
        return {
            'success': False,
            'message': f'Error al procesar archivo: {str(e)}'
        }
    
def _procesar_importacion_zip(file_path):
    """Procesar importación de archivo .zip"""
    try:
        with zipfile.ZipFile(file_path, 'r') as zip_ref:
            # Listar archivos en el ZIP
            files = zip_ref.namelist()
            db_files = [f for f in files if f.endswith('.db')]
            
            if not db_files:
                return {'success': False, 'message': 'No se encontraron archivos de base de datos en el ZIP'}
            
            # Extraer y procesar el primer archivo .db encontrado
            db_file = db_files[0]
            with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as temp_db:
                temp_db.write(zip_ref.read(db_file))
                temp_db.flush()
                
                resultado = _procesar_importacion_db(temp_db.name)
                
                try:
                    os.unlink(temp_db.name)
                except:
                    pass
                
                return resultado
                
    except Exception as e:
        return {'success': False, 'message': f'Error al procesar ZIP: {str(e)}'}