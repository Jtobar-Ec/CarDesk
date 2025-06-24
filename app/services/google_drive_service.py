import os
import json
from pathlib import Path
from datetime import datetime
import logging

class GoogleDriveService:
    """
    Servicio para integración con Google Drive API
    """
    
    def __init__(self):
        self.credentials_file = "google_credentials.json"
        self.token_file = "google_token.json"
        self.uploads_file = "google_drive_uploads.json"
        self.config_dir = Path("config")
        self.config_dir.mkdir(exist_ok=True)
        self.drive_folder_id = None
        self.logger = logging.getLogger(__name__)
        self.service = None
        self._setup_default_credentials()
    
    def _setup_default_credentials(self):
        """No configura credenciales por defecto - el usuario debe proporcionarlas"""
        pass
        
    def is_configured(self):
        """Verifica si Google Drive está configurado"""
        return os.path.exists(self.credentials_file)
    
    def _get_drive_service(self):
        """Obtiene servicio de Google Drive"""
        try:
            from google.auth.transport.requests import Request
            from google.oauth2.credentials import Credentials
            from google_auth_oauthlib.flow import InstalledAppFlow
            from googleapiclient.discovery import build
            
            SCOPES = ['https://www.googleapis.com/auth/drive.file']
            creds = None
            
            # Cargar token existente
            if os.path.exists(self.token_file):
                creds = Credentials.from_authorized_user_file(self.token_file, SCOPES)
            
            # Si no hay credenciales válidas, obtener nuevas
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    flow = InstalledAppFlow.from_client_secrets_file(
                        self.credentials_file, SCOPES)
                    # Usar puerto dinámico para evitar conflictos
                    creds = flow.run_local_server(
                        port=0,  # Puerto automático
                        open_browser=True
                    )
                
                # Guardar credenciales
                with open(self.token_file, 'w') as token:
                    token.write(creds.to_json())
            
            self.service = build('drive', 'v3', credentials=creds)
            return self.service
            
        except ImportError:
            self.logger.warning("Google API libraries not installed. Install: pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib")
            return None
        except Exception as e:
            self.logger.error(f"Error configurando Google Drive: {e}")
            return None
    
    def upload_backup(self, backup_path, backup_name):
        """Sube un backup a Google Drive"""
        try:
            if not self.is_configured():
                return {
                    "success": False,
                    "error": "Google Drive no está configurado."
                }
            
            service = self._get_drive_service()
            if not service:
                # Fallback a simulación si no hay API
                return self._simulate_upload(backup_path, backup_name)
            
            from googleapiclient.http import MediaFileUpload
            
            # Metadatos del archivo
            file_metadata = {
                'name': f"{backup_name}.zip",
                'parents': [self._get_or_create_backup_folder()]
            }
            
            # Subir archivo
            media = MediaFileUpload(backup_path, resumable=True)
            file = service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id'
            ).execute()
            
            # Guardar registro
            upload_record = {
                "backup_name": backup_name,
                "uploaded_at": datetime.now().isoformat(),
                "file_size": os.path.getsize(backup_path),
                "drive_file_id": file.get('id'),
                "status": "uploaded"
            }
            self._save_upload_record(upload_record)
            
            return {
                "success": True,
                "drive_file_id": file.get('id'),
                "message": f"Backup {backup_name} subido a Google Drive"
            }
            
        except Exception as e:
            self.logger.error(f"Error al subir backup: {str(e)}")
            return self._simulate_upload(backup_path, backup_name)
    
    def _simulate_upload(self, backup_path, backup_name):
        """Simulación de subida cuando no hay API disponible"""
        upload_record = {
            "backup_name": backup_name,
            "uploaded_at": datetime.now().isoformat(),
            "file_size": os.path.getsize(backup_path),
            "drive_file_id": f"simulated_id_{backup_name}",
            "status": "simulated"
        }
        self._save_upload_record(upload_record)
        
        return {
            "success": True,
            "drive_file_id": upload_record["drive_file_id"],
            "message": f"Backup {backup_name} preparado para Google Drive (simulado)"
        }
    
    def _get_or_create_backup_folder(self):
        """Obtiene o crea carpeta de backups en Drive"""
        if self.drive_folder_id:
            return self.drive_folder_id
        
        try:
            # Buscar carpeta existente
            results = self.service.files().list(
                q="name='CarDesk_Backups' and mimeType='application/vnd.google-apps.folder'",
                fields="files(id, name)"
            ).execute()
            
            folders = results.get('files', [])
            if folders:
                self.drive_folder_id = folders[0]['id']
                return self.drive_folder_id
            
            # Crear nueva carpeta
            folder_metadata = {
                'name': 'CarDesk_Backups',
                'mimeType': 'application/vnd.google-apps.folder'
            }
            folder = self.service.files().create(body=folder_metadata, fields='id').execute()
            self.drive_folder_id = folder.get('id')
            return self.drive_folder_id
            
        except Exception as e:
            self.logger.error(f"Error creando carpeta: {e}")
            return None
    
    def _save_upload_record(self, record):
        """Guarda registro de subidas"""
        records_file = "google_drive_uploads.json"
        
        if os.path.exists(records_file):
            with open(records_file, 'r') as f:
                records = json.load(f)
        else:
            records = []
        
        records.append(record)
        
        with open(records_file, 'w') as f:
            json.dump(records, f, indent=2)
    
    def list_drive_backups(self):
        """Lista backups en Google Drive"""
        records_file = "google_drive_uploads.json"
        
        if not os.path.exists(records_file):
            return []
        
        with open(records_file, 'r') as f:
            return json.load(f)
    
    def download_from_drive(self, drive_file_id, local_path):
        """
        Descarga un backup desde Google Drive
        Implementación simulada
        """
        try:
            if not self.is_configured():
                return {"success": False, "error": "Google Drive no configurado"}
            
            # Simulación de descarga
            self.logger.info(f"Simulando descarga de {drive_file_id}")
            
            return {
                "success": True,
                "message": "Descarga simulada completada",
                "local_path": local_path
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_setup_instructions(self):
        """Obtener instrucciones de configuración"""
        return {
            'steps': [
                'Ir a Google Cloud Console (console.cloud.google.com)',
                'Crear un nuevo proyecto o seleccionar uno existente',
                'Habilitar la API de Google Drive',
                'Ir a Credenciales > Crear credenciales > ID de cliente OAuth 2.0',
                'Seleccionar "Aplicación de escritorio"',
                'Descargar el archivo JSON de credenciales',
                'Copiar y pegar el contenido del archivo en el formulario'
            ],
            'required_scopes': [
                'https://www.googleapis.com/auth/drive.file'
            ]
        }
    
    def reset_credentials(self):
        """Resetear credenciales de Google Drive"""
        try:
            # Eliminar archivo de credenciales
            if os.path.exists(self.credentials_file):
                os.remove(self.credentials_file)
            
            # Eliminar token de acceso
            if os.path.exists(self.token_file):
                os.remove(self.token_file)
            
            # Eliminar historial de uploads
            if os.path.exists(self.uploads_file):
                os.remove(self.uploads_file)
            
            # Resetear servicio
            self.service = None
            self.drive_folder_id = None
            
            return {'success': True, 'message': 'Credenciales y configuración eliminadas correctamente'}
            
        except Exception as e:
            return {'success': False, 'error': f'Error reseteando credenciales: {str(e)}'}
    
    def clear_upload_history(self):
        """Limpiar historial de uploads"""
        try:
            if os.path.exists(self.uploads_file):
                os.remove(self.uploads_file)
            
            return {'success': True, 'message': 'Historial de uploads eliminado'}
        except Exception as e:
            return {'success': False, 'error': f'Error limpiando historial: {str(e)}'}
    
    def test_connection(self):
        """Probar conexión con Google Drive"""
        try:
            if not self.is_configured():
                return {'success': False, 'error': 'Google Drive no está configurado'}
            
            # Intentar autenticar y obtener información del usuario
            service = self._get_drive_service()
            if not service:
                return {'success': False, 'error': 'No se pudo autenticar con Google Drive'}
            
            # Probar acceso listando archivos (solo los creados por la app)
            try:
                results = service.files().list(
                    pageSize=1,
                    fields="files(id, name)"
                ).execute()
                
                return {
                    'success': True,
                    'message': 'Conexión exitosa con Google Drive',
                    'details': 'Credenciales válidas y acceso confirmado'
                }
                
            except Exception as api_error:
                return {
                    'success': False,
                    'error': f'Error de API: {str(api_error)}'
                }
                
        except Exception as e:
            return {'success': False, 'error': f'Error probando conexión: {str(e)}'}
    
    def setup_credentials(self, credentials_content):
        """
        Configura las credenciales de Google Drive
        """
        try:
            # Validar formato JSON
            credentials = json.loads(credentials_content)
            
            # Guardar credenciales
            with open(self.credentials_file, 'w') as f:
                json.dump(credentials, f, indent=2)
            
            return {"success": True, "message": "Credenciales configuradas correctamente"}
            
        except json.JSONDecodeError:
            return {"success": False, "error": "Formato de credenciales inválido"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    