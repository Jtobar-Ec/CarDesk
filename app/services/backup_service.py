import os
import json
import subprocess
import zipfile
import logging
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
import shutil
import mysql.connector
from mysql.connector import Error
from app.database import db
from app.database.models import Persona, Item, Articulo, Instrumento, Proveedor, MovimientoDetalle, Consumo, Entrada, Usuario
from .google_drive_service import GoogleDriveService

class BackupService:
    def __init__(self):
        # Configuración de directorios
        self.config_file = Path("backup_config.json")
        self.logger = logging.getLogger(__name__)
        self.load_config()
        self.drive_service = GoogleDriveService()
        # Configuración de MySQL
        self.db_config = self._get_db_config()
    
    def _get_db_config(self):
        """Obtener configuración de la base de datos desde las variables de entorno"""
        return {
            'host': os.getenv('DB_HOST', 'localhost'),
            'port': int(os.getenv('DB_PORT', 3306)),
            'user': os.getenv('DB_USER', 'flaskuser'),
            'password': os.getenv('DB_PASSWORD', 'flaskpass'),
            'database': os.getenv('DB_NAME', 'sistema_inventario')
        }
    
    def _test_db_connection(self):
        """Probar conexión a la base de datos MySQL"""
        try:
            connection = mysql.connector.connect(**self.db_config)
            if connection.is_connected():
                cursor = connection.cursor()
                cursor.execute("SELECT VERSION()")
                version = cursor.fetchone()
                cursor.close()
                connection.close()
                self.logger.debug(f"Conexión exitosa - MySQL {version[0]}")
                return True, f"Conexión exitosa - MySQL {version[0]}"
        except Error as e:
            self.logger.error(f"Error de conexión MySQL: {str(e)}")
            return False, f"Error de conexión MySQL: {str(e)}"
        except Exception as e:
            self.logger.error(f"Error inesperado: {str(e)}")
            return False, f"Error inesperado: {str(e)}"
    
    def load_config(self):
        """Carga configuración de directorios"""
        if self.config_file.exists():
            with open(self.config_file, 'r') as f:
                config = json.load(f)
                self.local_backup_dir = Path(config.get('local_backup_dir', 'backups/local'))
                self.first_time_setup = False
        else:
            # Primera vez - usar directorio por defecto pero marcar para configuración
            self.local_backup_dir = Path.cwd() / "backups" / "local"
            self.first_time_setup = True
        
        # Directorio cloud siempre en el proyecto
        self.backup_dir = Path.cwd() / "backups"
        self.cloud_backup_dir = self.backup_dir / "cloud"
        
        # Crear directorios
        self.local_backup_dir.mkdir(parents=True, exist_ok=True)
        self.cloud_backup_dir.mkdir(parents=True, exist_ok=True)
    
    def needs_directory_setup(self):
        """Verifica si necesita configuración inicial de directorio"""
        return self.first_time_setup
    
    def prompt_directory_setup(self):
        """Solicita configuración de directorio en primera ejecución"""
        try:
            import tkinter as tk
            from tkinter import filedialog, messagebox
            
            root = tk.Tk()
            root.withdraw()
            root.attributes('-topmost', True)
            
            # Mostrar mensaje de configuración inicial
            result = messagebox.askyesno(
                "Configuración Inicial - Kardex",
                "¿Desea seleccionar un directorio personalizado para guardar los backups locales?\n\n"
                "Si selecciona 'No', se usará el directorio por defecto del proyecto.",
                icon='question'
            )
            
            if result:
                directory = filedialog.askdirectory(
                    title="Seleccionar directorio para backups locales",
                    initialdir=str(Path.home())
                )
                root.destroy()
                
                if directory:
                    return self.set_local_backup_directory(directory)
                else:
                    # Usuario canceló, usar directorio por defecto
                    self._save_default_config()
                    return {"success": True, "directory": str(self.local_backup_dir)}
            else:
                root.destroy()
                # Usuario eligió directorio por defecto
                self._save_default_config()
                return {"success": True, "directory": str(self.local_backup_dir)}
                
        except ImportError:
            # Si no hay tkinter, usar directorio por defecto
            self._save_default_config()
            return {"success": True, "directory": str(self.local_backup_dir)}
        except Exception as e:
            self._save_default_config()
            return {"success": False, "error": str(e)}
    
    def _save_default_config(self):
        """Guarda configuración por defecto"""
        config = {'local_backup_dir': str(self.local_backup_dir)}
        with open(self.config_file, 'w') as f:
            json.dump(config, f, indent=2)
        self.first_time_setup = False
    
    def set_local_backup_directory(self, directory_path):
        """Configura directorio personalizado para backups locales"""
        try:
            new_dir = Path(directory_path)
            new_dir.mkdir(parents=True, exist_ok=True)
            
            # Guardar configuración
            config = {'local_backup_dir': str(new_dir)}
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=2)
            
            self.local_backup_dir = new_dir
            return {"success": True, "directory": str(new_dir)}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def set_custom_directory(self, directory):
        """Configurar directorio personalizado para backups locales"""
        return self.set_local_backup_directory(directory)
    
    def get_config(self):
        """Obtener configuración actual"""
        config = {}
        if self.config_file.exists():
            with open(self.config_file, 'r') as f:
                config = json.load(f)
        
        return {
            "custom_directory": config.get('local_backup_dir'),
            "use_custom_directory": bool(config.get('local_backup_dir'))
        }
    
    def reset_config(self):
        """Resetear configuración a valores por defecto"""
        try:
            # Eliminar archivo de configuración
            if self.config_file.exists():
                self.config_file.unlink()
            
            # Recargar configuración por defecto
            self.load_config()
            
            return {"success": True, "message": "Configuración reseteada correctamente"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def clear_all_backups(self):
        """Eliminar todos los backups existentes"""
        try:
            deleted_count = 0
            
            # Limpiar backups locales
            if self.local_backup_dir.exists():
                for backup_file in self.local_backup_dir.glob("*.zip"):
                    backup_file.unlink()
                    deleted_count += 1
            
            # Limpiar backups cloud
            if self.cloud_backup_dir.exists():
                for backup_file in self.cloud_backup_dir.glob("*.zip"):
                    backup_file.unlink()
                    deleted_count += 1
            
            return {"success": True, "message": f"Se eliminaron {deleted_count} backups"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def create_backup(self, backup_type="local"):
        """Crea un backup completo del sistema usando MySQL"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"kardex_backup_{backup_type}_{timestamp}"
        
        if backup_type == "local":
            backup_path = self.local_backup_dir / f"{backup_name}.zip"
        else:
            backup_path = self.cloud_backup_dir / f"{backup_name}.zip"
        
        try:
            # Verificar conexión a la base de datos
            is_connected, message = self._test_db_connection()
            if not is_connected:
                return {"success": False, "error": f"Error de conexión a MySQL: {message}"}
            
            # Crear directorio temporal
            temp_dir = tempfile.mkdtemp()
            sql_filename = f'{self.db_config["database"]}_backup_{timestamp}.sql'
            temp_sql_path = os.path.join(temp_dir, sql_filename)
            
            # Crear backup de MySQL usando mysqldump
            mysqldump_result = self._create_mysql_dump(temp_sql_path)
            if not mysqldump_result["success"]:
                shutil.rmtree(temp_dir)
                return mysqldump_result
            
            with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # 1. Backup de la base de datos MySQL
                zipf.write(temp_sql_path, f"database/{sql_filename}")
                
                # 2. Backup de datos en JSON (para compatibilidad)
                data_backup = self._export_data_to_json()
                zipf.writestr("data/backup_data.json", json.dumps(data_backup, indent=2, default=str))
                
                # 3. Información del backup
                backup_info = {
                    "created_at": datetime.now().isoformat(),
                    "backup_type": backup_type,
                    "version": "2.0",
                    "database_type": "mysql",
                    "database_name": self.db_config["database"],
                    "tables_included": ["personal", "articulos", "instrumentos", "proveedores", "movimientos", "consumos"]
                }
                zipf.writestr("backup_info.json", json.dumps(backup_info, indent=2))
            
            # Limpiar archivos temporales
            shutil.rmtree(temp_dir)
            
            result = {
                "success": True,
                "backup_path": str(backup_path),
                "backup_name": backup_name,
                "size": os.path.getsize(backup_path)
            }
            
            # Si es backup para la nube, intentar subir a Google Drive
            if backup_type == "cloud" and self.drive_service.is_configured():
                drive_result = self.drive_service.upload_backup(str(backup_path), backup_name)
                result["drive_upload"] = drive_result
            
            return result
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _create_mysql_dump(self, output_path):
        """Crear dump de MySQL usando mysqldump"""
        try:
            # Construir comando mysqldump
            mysqldump_command = [
                'mysqldump',
                f'-h{self.db_config["host"]}',
                f'-P{self.db_config["port"]}',
                f'-u{self.db_config["user"]}',
                f'-p{self.db_config["password"]}',
                '--routines',
                '--triggers',
                '--single-transaction',
                '--quick',
                '--lock-tables=false',
                self.db_config['database']
            ]
            
            self.logger.debug(f"Ejecutando mysqldump: {' '.join(mysqldump_command)}")
            
            # Ejecutar mysqldump
            with open(output_path, 'w') as output_file:
                result = subprocess.run(
                    mysqldump_command,
                    stdout=output_file,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=300  # 5 minutos timeout
                )
            
            if result.returncode != 0:
                self.logger.error(f"Error en mysqldump: {result.stderr}")
                return {"success": False, "error": f"Error en mysqldump: {result.stderr}"}
            
            # Verificar que el archivo se creó correctamente
            if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
                self.logger.error("El archivo de backup MySQL está vacío o no se pudo crear")
                return {"success": False, "error": "El archivo de backup MySQL está vacío o no se pudo crear"}
            
            return {"success": True, "sql_file": output_path}
            
        except subprocess.TimeoutExpired:
            self.logger.error("Timeout en mysqldump")
            return {"success": False, "error": "Timeout en mysqldump - la operación tardó demasiado"}
        except Exception as e:
            self.logger.error(f"Error ejecutando mysqldump: {str(e)}")
            return {"success": False, "error": f"Error ejecutando mysqldump: {str(e)}"}

    def _export_data_to_json(self):
        """Exporta todos los datos importantes a JSON"""
        data = {}
        
        # Personal
        personal = Persona.query.all()
        data["personal"] = [{
            "id": p.id,
            "codigo": p.pe_codigo,
            "nombre": p.pe_nombre,
            "apellido": p.pe_apellido,
            "ci": p.pe_ci,
            "telefono": p.pe_telefono,
            "correo": p.pe_correo,
            "direccion": p.pe_direccion,
            "cargo": p.pe_cargo,
            "estado": p.pe_estado,
            "created_at": p.created_at.isoformat() if p.created_at else None
        } for p in personal]
        
        # Items (base para artículos e instrumentos)
        items = Item.query.all()
        data["items"] = [{
            "id": i.id,
            "codigo": i.i_codigo,
            "nombre": i.i_nombre,
            "tipo": i.i_tipo,
            "cantidad": i.i_cantidad,
            "valor_unitario": float(i.i_vUnitario),
            "valor_total": float(i.i_vTotal),
            "created_at": i.created_at.isoformat() if i.created_at else None
        } for i in items]
        
        # Artículos
        articulos = Articulo.query.all()
        data["articulos"] = [{
            "item_id": a.i_id,
            "cuenta_contable": a.a_c_contable,
            "stock_min": a.a_stockMin,
            "stock_max": a.a_stockMax,
            "created_at": a.created_at.isoformat() if a.created_at else None
        } for a in articulos]
        
        # Instrumentos
        instrumentos = Instrumento.query.all()
        data["instrumentos"] = [{
            "item_id": i.i_id,
            "marca": i.i_marca,
            "modelo": i.i_modelo,
            "serie": i.i_serie,
            "estado": i.i_estado,
            "created_at": i.created_at.isoformat() if i.created_at else None
        } for i in instrumentos]
        
        # Proveedores
        proveedores = Proveedor.query.all()
        data["proveedores"] = [{
            "id": p.id,
            "codigo": p.p_codigo,
            "razon_social": p.p_razonsocial,
            "ci_ruc": p.p_ci_ruc,
            "direccion": p.p_direccion,
            "telefono": p.p_telefono,
            "correo": p.p_correo,
            "created_at": p.created_at.isoformat() if p.created_at else None
        } for p in proveedores]
        
        # Movimientos
        movimientos = MovimientoDetalle.query.all()
        data["movimientos"] = [{
            "id": m.id,
            "fecha": m.m_fecha.isoformat() if m.m_fecha else None,
            "tipo": m.m_tipo,
            "cantidad": m.m_cantidad,
            "valor_unitario": float(m.m_valorUnitario),
            "valor_total": float(m.m_valorTotal),
            "observaciones": m.m_observaciones,
            "item_id": m.i_id,
            "usuario_id": m.u_id,
            "created_at": m.created_at.isoformat() if m.created_at else None
        } for m in movimientos]
        
        # Consumos/Asignaciones
        consumos = Consumo.query.all()
        data["consumos"] = [{
            "id": c.id,
            "numero": c.c_numero,
            "fecha": c.c_fecha.isoformat() if c.c_fecha else None,
            "hora": c.c_hora.isoformat() if c.c_hora else None,
            "descripcion": c.c_descripcion,
            "cantidad": c.c_cantidad,
            "valor_unitario": float(c.c_valorUnitario),
            "valor_total": float(c.c_valorTotal),
            "observaciones": c.c_observaciones,
            "estado": c.c_estado,
            "persona_id": c.pe_id,
            "item_id": c.i_id,
            "usuario_id": c.u_id,
            "created_at": c.created_at.isoformat() if c.created_at else None
        } for c in consumos]
        
        return data

    def list_backups(self, backup_type="all"):
        """Lista backups disponibles filtrados por configuración actual"""
        backups = []
        
        # Backups locales: solo del directorio configurado por el usuario
        if backup_type in ["all", "local"]:
            if self.local_backup_dir.exists():
                for backup_file in self.local_backup_dir.glob("*.zip"):
                    backups.append(self._get_backup_info(backup_file, "local"))
        
        # Backups cloud: solo los relacionados con la cuenta de Google Drive configurada
        if backup_type in ["all", "cloud"]:
            # Obtener backups locales en directorio cloud
            if self.cloud_backup_dir.exists():
                for backup_file in self.cloud_backup_dir.glob("*.zip"):
                    backups.append(self._get_backup_info(backup_file, "cloud"))
            
            # Agregar backups de Google Drive si está configurado
            if self.drive_service.is_configured():
                drive_backups = self._get_drive_backups()
                backups.extend(drive_backups)
        
        return sorted(backups, key=lambda x: x["created_at"], reverse=True)
    
    def _get_drive_backups(self):
        """Obtiene lista de backups desde Google Drive"""
        try:
            drive_records = self.drive_service.list_drive_backups()
            drive_backups = []
            
            for record in drive_records:
                # Solo incluir backups de la cuenta actual
                if record.get('status') in ['uploaded', 'simulated']:
                    drive_backups.append({
                        "name": record['backup_name'],
                        "path": f"drive://{record['drive_file_id']}",
                        "type": "cloud_drive",
                        "size": record['file_size'],
                        "created_at": datetime.fromisoformat(record['uploaded_at'].replace('Z', '+00:00')),
                        "size_mb": round(record['file_size'] / (1024 * 1024), 2),
                        "drive_file_id": record['drive_file_id']
                    })
            
            return drive_backups
        except Exception as e:
            self.logger.error(f"Error obteniendo backups de Drive: {e}")
            return []

    def _get_backup_info(self, backup_path, backup_type):
        """Obtiene información de un backup"""
        stat = backup_path.stat()
        return {
            "name": backup_path.stem,
            "path": str(backup_path),
            "type": backup_type,
            "size": stat.st_size,
            "created_at": datetime.fromtimestamp(stat.st_mtime),
            "size_mb": round(stat.st_size / (1024 * 1024), 2)
        }

    def restore_backup(self, backup_path):
        """Restaura un backup MySQL con validaciones mejoradas"""
        try:
            # Manejar backups de Google Drive
            if backup_path.startswith("drive://"):
                return self._restore_from_drive(backup_path)
            
            backup_path = Path(backup_path)
            
            # Si no existe, intentar encontrarlo en los directorios configurados
            if not backup_path.exists():
                found_path = self._find_backup_file(str(backup_path))
                if not found_path:
                    return {"success": False, "error": "Archivo de backup no encontrado"}
                backup_path = found_path
            
            # Validar que es un archivo ZIP válido
            if not zipfile.is_zipfile(backup_path):
                return {"success": False, "error": "El archivo no es un backup válido"}
            
            # Validar contenido del backup antes de proceder
            with zipfile.ZipFile(backup_path, 'r') as zipf:
                files_in_backup = zipf.namelist()
                sql_files = [f for f in files_in_backup if f.startswith("database/") and f.endswith(".sql")]
                
                if not sql_files:
                    # Verificar si es un backup antiguo de SQLite
                    if "database/conservatorio.db" in files_in_backup:
                        return {"success": False, "error": "Este backup es de SQLite y no es compatible con MySQL. Use la migración para convertir datos."}
                    return {"success": False, "error": "El backup no contiene archivos SQL de MySQL"}
            
            # Verificar conexión a MySQL
            is_connected, message = self._test_db_connection()
            if not is_connected:
                return {"success": False, "error": f"Error de conexión a MySQL: {message}"}
            
            # Crear backup de seguridad de la BD actual
            safety_backup_created = False
            try:
                safety_result = self._create_safety_backup()
                safety_backup_created = safety_result.get("success", False)
            except Exception as e:
                self.logger.warning(f"No se pudo crear backup de seguridad: {e}")
            
            # Crear directorio temporal
            temp_dir = tempfile.mkdtemp()
            
            try:
                with zipfile.ZipFile(backup_path, 'r') as zipf:
                    # Extraer archivo SQL
                    sql_file = sql_files[0]  # Tomar el primer archivo SQL encontrado
                    zipf.extract(sql_file, temp_dir)
                    sql_path = os.path.join(temp_dir, sql_file)
                    
                    # Verificar que el archivo extraído existe y tiene contenido
                    if not os.path.exists(sql_path) or os.path.getsize(sql_path) == 0:
                        return {"success": False, "error": "El archivo SQL en el backup está corrupto"}
                    
                    # Restaurar base de datos MySQL
                    restore_result = self._restore_mysql_dump(sql_path)
                    if not restore_result["success"]:
                        return restore_result
                
                return {
                    "success": True,
                    "safety_backup_created": safety_backup_created,
                    "message": "Backup MySQL restaurado exitosamente",
                    "restored_from": str(backup_path)
                }
                
            finally:
                # Limpiar directorio temporal
                if os.path.exists(temp_dir):
                    shutil.rmtree(temp_dir, ignore_errors=True)
            
        except zipfile.BadZipFile:
            return {"success": False, "error": "El archivo de backup está corrupto"}
        except PermissionError:
            return {"success": False, "error": "Sin permisos para acceder al archivo de backup"}
        except Exception as e:
            return {"success": False, "error": f"Error durante la restauración: {str(e)}"}
    
    def _create_safety_backup(self):
        """Crear backup de seguridad antes de restaurar"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safety_backup_name = f"safety_backup_{timestamp}"
            return self.create_backup("local")
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _restore_mysql_dump(self, sql_file_path):
        """Restaurar base de datos MySQL desde archivo SQL"""
        try:
            # Construir comando mysql para importar
            mysql_command = [
                'mysql',
                f'-h{self.db_config["host"]}',
                f'-P{self.db_config["port"]}',
                f'-u{self.db_config["user"]}',
                f'-p{self.db_config["password"]}',
                self.db_config['database']
            ]
            
            self.logger.debug(f"Ejecutando mysql import: {' '.join(mysql_command)}")
            
            # Ejecutar comando mysql
            with open(sql_file_path, 'r') as input_file:
                result = subprocess.run(
                    mysql_command,
                    stdin=input_file,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=600  # 10 minutos timeout
                )
            
            if result.returncode != 0:
                self.logger.error(f"Error en mysql import: {result.stderr}")
                return {"success": False, "error": f"Error en mysql import: {result.stderr}"}
            
            return {"success": True, "message": "Base de datos MySQL restaurada exitosamente"}
            
        except subprocess.TimeoutExpired:
            self.logger.error("Timeout en mysql import")
            return {"success": False, "error": "Timeout en mysql import - la operación tardó demasiado"}
        except Exception as e:
            self.logger.error(f"Error ejecutando mysql import: {str(e)}")
            return {"success": False, "error": f"Error ejecutando mysql import: {str(e)}"}
    
    def _restore_from_drive(self, drive_path):
        """Restaura un backup desde Google Drive"""
        try:
            drive_file_id = drive_path.replace("drive://", "")
            
            # Descargar desde Google Drive
            temp_backup = Path("temp_drive_backup.zip")
            download_result = self.drive_service.download_from_drive(drive_file_id, str(temp_backup))
            
            if not download_result.get('success'):
                return {"success": False, "error": f"Error descargando desde Drive: {download_result.get('error')}"}
            
            # Restaurar el archivo descargado
            result = self.restore_backup(str(temp_backup))
            
            # Limpiar archivo temporal
            if temp_backup.exists():
                temp_backup.unlink()
            
            return result
            
        except Exception as e:
            return {"success": False, "error": f"Error restaurando desde Drive: {str(e)}"}
    
    def _find_backup_file(self, backup_path):
        """Busca un archivo de backup en los directorios configurados"""
        backup_path = Path(backup_path)
        backup_name = backup_path.name
        
        # Buscar en directorio local configurado
        local_file = self.local_backup_dir / backup_name
        if local_file.exists():
            return local_file
        
        # Buscar en directorio cloud
        cloud_file = self.cloud_backup_dir / backup_name
        if cloud_file.exists():
            return cloud_file
        
        # Si solo se pasó el nombre, buscar archivos que contengan ese nombre
        if not backup_name.endswith('.zip'):
            backup_name += '.zip'
            
        # Buscar en directorio local
        for backup_file in self.local_backup_dir.glob("*.zip"):
            if backup_name in backup_file.name or backup_file.name == backup_name:
                return backup_file
        
        # Buscar en directorio cloud
        for backup_file in self.cloud_backup_dir.glob("*.zip"):
            if backup_name in backup_file.name or backup_file.name == backup_name:
                return backup_file
        
        return None

    def cleanup_old_backups(self):
        """Limpia backups antiguos según política de retención"""
        # Mantener backups locales por 30 días
        cutoff_date = datetime.now() - timedelta(days=30)
        
        for backup_file in self.local_backup_dir.glob("*.zip"):
            if datetime.fromtimestamp(backup_file.stat().st_mtime) < cutoff_date:
                backup_file.unlink()
        
        # Mantener backups en la nube por 6 meses
        cloud_cutoff = datetime.now() - timedelta(days=180)
        for backup_file in self.cloud_backup_dir.glob("*.zip"):
            if datetime.fromtimestamp(backup_file.stat().st_mtime) < cloud_cutoff:
                backup_file.unlink()

    def schedule_automatic_backups(self):
        """Programa backups automáticos"""
        # Esta función será llamada por un scheduler
        now = datetime.now()
        
        # Backup semanal local
        if now.weekday() == 6:  # Domingo
            self.create_backup("local")
        
        # Backup mensual (primer domingo del mes)
        if now.weekday() == 6 and now.day <= 7:
            self.create_backup("cloud")
        
        # Limpiar backups antiguos
        self.cleanup_old_backups()