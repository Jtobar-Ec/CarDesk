import threading
import time
from datetime import datetime, timedelta
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
    
    def _check_and_run_backups(self):
        """Verifica si es momento de ejecutar backups"""
        now = datetime.now()
        
        # Backup semanal (domingos a las 2:00 AM)
        if now.weekday() == 6 and now.hour == 2 and now.minute < 5:
            self._run_weekly_backup()
        
        # Backup mensual (primer domingo del mes a las 3:00 AM)
        if (now.weekday() == 6 and now.day <= 7 and 
            now.hour == 3 and now.minute < 5):
            self._run_monthly_backup()
        
        # Limpieza diaria (todos los días a las 4:00 AM)
        if now.hour == 4 and now.minute < 5:
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
        
        # Próximo domingo a las 2:00 AM para backup semanal
        days_until_sunday = (6 - now.weekday()) % 7
        if days_until_sunday == 0 and now.hour >= 2:
            days_until_sunday = 7
        
        next_weekly = now.replace(hour=2, minute=0, second=0, microsecond=0) + timedelta(days=days_until_sunday)
        
        # Primer domingo del próximo mes a las 3:00 AM
        next_month = now.replace(day=1) + timedelta(days=32)
        next_month = next_month.replace(day=1)
        
        # Encontrar primer domingo del mes
        days_to_first_sunday = (6 - next_month.weekday()) % 7
        next_monthly = next_month.replace(hour=3, minute=0, second=0, microsecond=0) + timedelta(days=days_to_first_sunday)
        
        return {
            "next_weekly": next_weekly.isoformat(),
            "next_monthly": next_monthly.isoformat(),
            "scheduler_running": self.running
        }

# Instancia global del scheduler
backup_scheduler = BackupScheduler()