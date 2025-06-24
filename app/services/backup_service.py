import os
import json
import sqlite3
import zipfile
from datetime import datetime, timedelta
from pathlib import Path
import shutil
from app import db
from app.database.models import Persona, Item, Articulo, Instrumento, Proveedor, MovimientoDetalle, Consumo
from .google_drive_service import GoogleDriveService

class BackupService:
    def __init__(self):
        # Configuración de directorios
        self.config_file = Path("backup_config.json")
        self.load_config()
        self.drive_service = GoogleDriveService()
    
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
        """Crea un backup completo del sistema"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"kardex_backup_{backup_type}_{timestamp}"
        
        if backup_type == "local":
            backup_path = self.local_backup_dir / f"{backup_name}.zip"
        else:
            backup_path = self.cloud_backup_dir / f"{backup_name}.zip"
        
        try:
            with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # 1. Backup de la base de datos (ruta multiplataforma)
                db_path = Path("instance") / "conservatorio.db"
                if db_path.exists():
                    zipf.write(str(db_path), "database/conservatorio.db")
                
                # 2. Backup de datos en JSON
                data_backup = self._export_data_to_json()
                zipf.writestr("data/backup_data.json", json.dumps(data_backup, indent=2, default=str))
                
                # 3. Información del backup
                backup_info = {
                    "created_at": datetime.now().isoformat(),
                    "backup_type": backup_type,
                    "version": "1.0",
                    "tables_included": ["personal", "articulos", "instrumentos", "proveedores", "movimientos", "consumos"]
                }
                zipf.writestr("backup_info.json", json.dumps(backup_info, indent=2))
            
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
        """Lista todos los backups disponibles"""
        backups = []
        
        if backup_type in ["all", "local"]:
            for backup_file in self.local_backup_dir.glob("*.zip"):
                backups.append(self._get_backup_info(backup_file, "local"))
        
        if backup_type in ["all", "cloud"]:
            for backup_file in self.cloud_backup_dir.glob("*.zip"):
                backups.append(self._get_backup_info(backup_file, "cloud"))
        
        return sorted(backups, key=lambda x: x["created_at"], reverse=True)

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
        """Restaura un backup (multiplataforma)"""
        try:
            backup_path = Path(backup_path)
            if not backup_path.exists():
                return {"success": False, "error": "Archivo de backup no encontrado"}
            
            # Crear backup de seguridad antes de restaurar
            current_backup = self.create_backup("restore_safety")
            
            # Crear directorio temporal multiplataforma
            temp_dir = Path("temp_restore")
            instance_dir = Path("instance")
            instance_dir.mkdir(exist_ok=True)
            
            with zipfile.ZipFile(backup_path, 'r') as zipf:
                # Restaurar base de datos
                if "database/conservatorio.db" in zipf.namelist():
                    zipf.extract("database/conservatorio.db", temp_dir)
                    db_source = temp_dir / "database" / "conservatorio.db"
                    db_target = instance_dir / "conservatorio.db"
                    
                    if db_source.exists():
                        shutil.move(str(db_source), str(db_target))
                    
                    # Limpiar directorio temporal
                    if temp_dir.exists():
                        shutil.rmtree(temp_dir, ignore_errors=True)
            
            return {"success": True, "safety_backup": current_backup}
        except Exception as e:
            return {"success": False, "error": str(e)}

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