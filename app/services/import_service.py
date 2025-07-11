import os
import subprocess
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path
from flask import current_app
import logging

class ImportService:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
    def get_db_config(self):
        """Obtener configuración de la base de datos desde la configuración de Flask"""
        return {
            'host': current_app.config.get('MYSQL_HOST', 'localhost'),
            'port': current_app.config.get('MYSQL_PORT', '3306'),
            'user': current_app.config.get('MYSQL_USER', 'flaskuser'),
            'password': current_app.config.get('MYSQL_PASSWORD', 'flaskpass'),
            'database': current_app.config.get('MYSQL_DATABASE', 'sistema_inventario')
        }
    
    def validate_sql_file(self, file_path):
        """Validar que el archivo SQL sea un dump válido de MySQL"""
        try:
            if not os.path.exists(file_path):
                return {'valid': False, 'message': 'Archivo no encontrado'}
            
            if os.path.getsize(file_path) == 0:
                return {'valid': False, 'message': 'El archivo está vacío'}
            
            # Leer una muestra del archivo
            with open(file_path, 'r', encoding='utf-8') as f:
                sample = f.read(4096)
            
            # Verificar indicadores de dump MySQL
            mysql_indicators = [
                'MySQL dump',
                'CREATE TABLE',
                'INSERT INTO',
                'DROP TABLE IF EXISTS'
            ]
            
            if not any(indicator in sample for indicator in mysql_indicators):
                return {'valid': False, 'message': 'El archivo no parece ser un dump válido de MySQL'}
            
            # Verificar que contenga tablas del sistema
            expected_tables = ['tb_item', 'tb_usuario', 'tb_persona']
            has_system_tables = any(table in sample for table in expected_tables)
            
            if not has_system_tables:
                return {'valid': False, 'message': 'El archivo no contiene las tablas esperadas del sistema'}
            
            return {'valid': True, 'message': 'Archivo SQL válido'}
            
        except UnicodeDecodeError:
            return {'valid': False, 'message': 'Error de codificación. El archivo debe estar en UTF-8'}
        except Exception as e:
            return {'valid': False, 'message': f'Error al validar archivo: {str(e)}'}
    
    def create_backup(self, backup_dir='temp_uploads'):
        """Crear backup de seguridad antes de importar"""
        try:
            db_config = self.get_db_config()
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_filename = f"backup_antes_importacion_{timestamp}.sql"
            backup_path = os.path.join(backup_dir, backup_filename)
            
            # Crear directorio si no existe
            os.makedirs(backup_dir, exist_ok=True)
            
            # Comando mysqldump
            dump_command = [
                'mysqldump',
                f'-h{db_config["host"]}',
                f'-P{db_config["port"]}',
                f'-u{db_config["user"]}',
                f'-p{db_config["password"]}',
                '--single-transaction',
                '--routines',
                '--triggers',
                '--add-drop-table',
                '--complete-insert',
                db_config['database']
            ]
            
            # Ejecutar backup
            with open(backup_path, 'w', encoding='utf-8') as backup_file:
                result = subprocess.run(
                    dump_command,
                    stdout=backup_file,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=300
                )
            
            if result.returncode == 0:
                return {
                    'success': True,
                    'backup_path': backup_path,
                    'message': 'Backup de seguridad creado exitosamente'
                }
            else:
                self.logger.warning(f"No se pudo crear backup: {result.stderr}")
                return {
                    'success': False,
                    'message': f'Error creando backup: {result.stderr}'
                }
                
        except subprocess.TimeoutExpired:
            return {'success': False, 'message': 'Timeout creando backup de seguridad'}
        except Exception as e:
            self.logger.error(f"Error creando backup: {str(e)}")
            return {'success': False, 'message': f'Error creando backup: {str(e)}'}
    
    def import_sql_file(self, file_path, create_backup=True):
        """Importar archivo SQL a la base de datos MySQL"""
        try:
            # Validar archivo
            validation = self.validate_sql_file(file_path)
            if not validation['valid']:
                return {'success': False, 'message': validation['message']}
            
            db_config = self.get_db_config()
            backup_created = False
            backup_path = None
            
            # Crear backup de seguridad
            if create_backup:
                backup_result = self.create_backup()
                backup_created = backup_result['success']
                backup_path = backup_result.get('backup_path')
                if not backup_created:
                    self.logger.warning(f"No se pudo crear backup: {backup_result['message']}")
            
            # Comando mysql para importar
            import_command = [
                'mysql',
                f'-h{db_config["host"]}',
                f'-P{db_config["port"]}',
                f'-u{db_config["user"]}',
                f'-p{db_config["password"]}',
                '--default-character-set=utf8mb4',
                db_config['database']
            ]
            
            # Ejecutar importación
            with open(file_path, 'r', encoding='utf-8') as sql_file:
                result = subprocess.run(
                    import_command,
                    stdin=sql_file,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=600  # 10 minutos
                )
            
            # Verificar resultado
            if result.returncode != 0:
                error_msg = result.stderr.strip()
                
                # Filtrar advertencias que no son errores críticos
                if 'Warning' in error_msg and 'Error' not in error_msg:
                    return {
                        'success': True,
                        'message': f'Importación completada con advertencias: {error_msg}',
                        'backup_created': backup_created,
                        'backup_path': backup_path
                    }
                else:
                    return {
                        'success': False,
                        'message': f'Error durante la importación: {error_msg}',
                        'backup_created': backup_created,
                        'backup_path': backup_path
                    }
            
            # Verificar que la importación fue exitosa
            verification = self.verify_import(db_config)
            
            return {
                'success': True,
                'message': f'Base de datos importada exitosamente. {verification["tables_count"]} tablas detectadas.',
                'backup_created': backup_created,
                'backup_path': backup_path,
                'tables_imported': verification['tables_count']
            }
            
        except subprocess.TimeoutExpired:
            return {
                'success': False,
                'message': 'La importación excedió el tiempo límite (10 minutos)',
                'backup_created': backup_created,
                'backup_path': backup_path
            }
        except Exception as e:
            self.logger.error(f"Error durante importación: {str(e)}")
            return {
                'success': False,
                'message': f'Error durante la importación: {str(e)}',
                'backup_created': backup_created,
                'backup_path': backup_path
            }
    
    def verify_import(self, db_config):
        """Verificar que la importación fue exitosa"""
        try:
            verify_command = [
                'mysql',
                f'-h{db_config["host"]}',
                f'-P{db_config["port"]}',
                f'-u{db_config["user"]}',
                f'-p{db_config["password"]}',
                '-e', 'SHOW TABLES;',
                db_config['database']
            ]
            
            result = subprocess.run(
                verify_command,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0 and result.stdout.strip():
                tables = result.stdout.strip().split('\n')[1:]  # Excluir header
                return {
                    'success': True,
                    'tables_count': len(tables),
                    'tables': tables
                }
            else:
                return {
                    'success': False,
                    'tables_count': 0,
                    'message': 'No se detectaron tablas'
                }
                
        except Exception as e:
            return {
                'success': False,
                'tables_count': 0,
                'message': f'Error verificando importación: {str(e)}'
            }
    
    def import_zip_file(self, zip_path):
        """Importar archivo ZIP que contiene dump SQL"""
        try:
            if not zipfile.is_zipfile(zip_path):
                return {'success': False, 'message': 'El archivo ZIP está corrupto'}
            
            with tempfile.TemporaryDirectory() as temp_dir:
                # Extraer ZIP
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall(temp_dir)
                
                # Buscar archivos SQL
                sql_files = []
                for root, dirs, files in os.walk(temp_dir):
                    for file in files:
                        if file.endswith('.sql'):
                            sql_files.append(os.path.join(root, file))
                
                if not sql_files:
                    return {'success': False, 'message': 'No se encontraron archivos SQL en el ZIP'}
                
                # Importar el primer archivo SQL encontrado
                sql_file = sql_files[0]
                return self.import_sql_file(sql_file)
                
        except Exception as e:
            return {'success': False, 'message': f'Error procesando archivo ZIP: {str(e)}'}
    
    def get_import_status(self):
        """Obtener estado actual de la base de datos"""
        try:
            db_config = self.get_db_config()
            verification = self.verify_import(db_config)
            
            if verification['success']:
                return {
                    'success': True,
                    'tables_count': verification['tables_count'],
                    'tables': verification.get('tables', []),
                    'database': db_config['database']
                }
            else:
                return {
                    'success': False,
                    'message': verification['message']
                }
                
        except Exception as e:
            return {'success': False, 'message': f'Error obteniendo estado: {str(e)}'}