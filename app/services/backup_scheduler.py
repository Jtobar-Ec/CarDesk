import threading
import time
import json
import os
from datetime import datetime, timedelta
from pathlib import Path
import logging
from .backup_service import BackupService
from .google_drive_service import GoogleDriveService

class BackupScheduler:
    """
    Scheduler para backups automáticos
    """
    
    def __init__(self):
        self.backup_service = BackupService()
        self.drive_service = GoogleDriveService()
        self.logger = logging.getLogger(__name__)
        self.running = False
        self.thread = None
        self.config_file = Path("backup_schedule_config.json")
        self.load_schedule_config()
        
    def start(self):
        """Inicia el scheduler de backups"""
        if self.running:
            return
            
        self.running = True
        self.thread = threading.Thread(target=self._run_scheduler, daemon=True)
        self.thread.start()
        self.logger.info("Scheduler de backups iniciado")
    
    def stop(self):
        """Detiene el scheduler"""
        self.running = False
        if self.thread:
            self.thread.join()
        self.logger.info("Scheduler de backups detenido")
    
    def _run_scheduler(self):
        """Ejecuta el loop principal del scheduler"""
        while self.running:
            try:
                self._check_and_run_backups()
                # Verificar cada hora
                time.sleep(3600)
            except Exception as e:
                self.logger.error(f"Error en scheduler: {str(e)}")
                time.sleep(300)  # Esperar 5 minutos en caso de error
    
    def load_schedule_config(self):
        """Carga configuración de horarios desde archivo"""
        default_config = {
            "weekly": {
                "enabled": True,
                "day": 6,  # 0=Lunes, 6=Domingo
                "hour": 2,
                "minute": 0
            },
            "monthly": {
                "enabled": True,
                "day": 6,  # Primer domingo del mes
                "hour": 3,
                "minute": 0
            },
            "cleanup": {
                "enabled": True,
                "hour": 4,
                "minute": 0
            }
        }
        
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    self.schedule_config = json.load(f)
                # Validar y completar configuración faltante
                for key in default_config:
                    if key not in self.schedule_config:
                        self.schedule_config[key] = default_config[key]
            except Exception as e:
                self.logger.error(f"Error cargando configuración de horarios: {e}")
                self.schedule_config = default_config
        else:
            self.schedule_config = default_config
            self.save_schedule_config()
    
    def save_schedule_config(self):
        """Guarda configuración de horarios"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.schedule_config, f, indent=2)
        except Exception as e:
            self.logger.error(f"Error guardando configuración de horarios: {e}")
    
    def update_schedule_config(self, backup_type, config):
        """Actualiza configuración de horarios"""
        if backup_type in self.schedule_config:
            self.schedule_config[backup_type].update(config)
            self.save_schedule_config()
            return {"success": True, "message": f"Configuración de {backup_type} actualizada"}
        return {"success": False, "error": "Tipo de backup no válido"}
    
    def get_schedule_config(self):
        """Obtiene configuración actual de horarios"""
        return self.schedule_config.copy()
    
    def _check_and_run_backups(self):
        """Verifica si es momento de ejecutar backups"""
        now = datetime.now()
        
        # Backup semanal
        weekly_config = self.schedule_config.get("weekly", {})
        if (weekly_config.get("enabled", True) and
            now.weekday() == weekly_config.get("day", 6) and
            now.hour == weekly_config.get("hour", 2) and
            now.minute < 5):
            self._run_weekly_backup()
        
        # Backup mensual (primer día configurado del mes)
        monthly_config = self.schedule_config.get("monthly", {})
        if (monthly_config.get("enabled", True) and
            now.weekday() == monthly_config.get("day", 6) and
            now.day <= 7 and
            now.hour == monthly_config.get("hour", 3) and
            now.minute < 5):
            self._run_monthly_backup()
        
        # Limpieza diaria
        cleanup_config = self.schedule_config.get("cleanup", {})
        if (cleanup_config.get("enabled", True) and
            now.hour == cleanup_config.get("hour", 4) and
            now.minute < 5):
            self._run_cleanup()
    
    def _run_weekly_backup(self):
        """Ejecuta backup semanal local"""
        try:
            self.logger.info("Iniciando backup semanal automático")
            result = self.backup_service.create_backup("local")
            
            if result['success']:
                self.logger.info(f"Backup semanal creado: {result['backup_name']}")
            else:
                self.logger.error(f"Error en backup semanal: {result['error']}")
                
        except Exception as e:
            self.logger.error(f"Error ejecutando backup semanal: {str(e)}")
    
    def _run_monthly_backup(self):
        """Ejecuta backup mensual para la nube"""
        try:
            self.logger.info("Iniciando backup mensual automático")
            
            # Crear backup local primero
            result = self.backup_service.create_backup("cloud")
            
            if result['success']:
                self.logger.info(f"Backup mensual creado: {result['backup_name']}")
                
                # Intentar subir a Google Drive si está configurado
                if self.drive_service.is_configured():
                    drive_result = self.drive_service.upload_backup(
                        result['backup_path'], 
                        result['backup_name']
                    )
                    
                    if drive_result['success']:
                        self.logger.info(f"Backup subido a Google Drive: {drive_result['drive_file_id']}")
                    else:
                        self.logger.warning(f"No se pudo subir a Google Drive: {drive_result['error']}")
                else:
                    self.logger.info("Google Drive no configurado, backup guardado localmente")
            else:
                self.logger.error(f"Error en backup mensual: {result['error']}")
                
        except Exception as e:
            self.logger.error(f"Error ejecutando backup mensual: {str(e)}")
    
    def _run_cleanup(self):
        """Ejecuta limpieza de backups antiguos"""
        try:
            self.logger.info("Iniciando limpieza automática de backups")
            self.backup_service.cleanup_old_backups()
            self.logger.info("Limpieza de backups completada")
            
        except Exception as e:
            self.logger.error(f"Error en limpieza de backups: {str(e)}")
    
    def force_backup(self, backup_type="local"):
        """Fuerza la ejecución de un backup"""
        try:
            self.logger.info(f"Forzando backup {backup_type}")
            
            if backup_type == "weekly":
                self._run_weekly_backup()
            elif backup_type == "monthly":
                self._run_monthly_backup()
            else:
                result = self.backup_service.create_backup(backup_type)
                return result
                
        except Exception as e:
            self.logger.error(f"Error forzando backup: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def get_next_scheduled_backups(self):
        """Retorna información sobre próximos backups programados"""
        now = datetime.now()
        
        # Configuración semanal
        weekly_config = self.schedule_config.get("weekly", {})
        weekly_day = weekly_config.get("day", 6)
        weekly_hour = weekly_config.get("hour", 2)
        weekly_minute = weekly_config.get("minute", 0)
        
        # Calcular próximo backup semanal
        days_until_weekly = (weekly_day - now.weekday()) % 7
        if days_until_weekly == 0 and (now.hour > weekly_hour or (now.hour == weekly_hour and now.minute >= weekly_minute)):
            days_until_weekly = 7
        
        next_weekly = now.replace(hour=weekly_hour, minute=weekly_minute, second=0, microsecond=0) + timedelta(days=days_until_weekly)
        
        # Configuración mensual
        monthly_config = self.schedule_config.get("monthly", {})
        monthly_day = monthly_config.get("day", 6)
        monthly_hour = monthly_config.get("hour", 3)
        monthly_minute = monthly_config.get("minute", 0)
        
        # Calcular próximo backup mensual (primer día configurado del mes)
        next_month = now.replace(day=1) + timedelta(days=32)
        next_month = next_month.replace(day=1)
        
        # Encontrar primer día configurado del mes
        days_to_target = (monthly_day - next_month.weekday()) % 7
        next_monthly = next_month.replace(hour=monthly_hour, minute=monthly_minute, second=0, microsecond=0) + timedelta(days=days_to_target)
        
        # Si ya pasó este mes, calcular para el próximo
        if next_monthly <= now:
            next_month = next_month.replace(day=1) + timedelta(days=32)
            next_month = next_month.replace(day=1)
            days_to_target = (monthly_day - next_month.weekday()) % 7
            next_monthly = next_month.replace(hour=monthly_hour, minute=monthly_minute, second=0, microsecond=0) + timedelta(days=days_to_target)
        
        return {
            "next_weekly": next_weekly.isoformat() if weekly_config.get("enabled", True) else None,
            "next_monthly": next_monthly.isoformat() if monthly_config.get("enabled", True) else None,
            "scheduler_running": self.running,
            "config": self.schedule_config
        }

# Instancia global del scheduler
backup_scheduler = BackupScheduler()