from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for, send_file
from app.services.backup_service import BackupService
from app.services.google_drive_service import GoogleDriveService
from app.services.backup_scheduler import backup_scheduler
from datetime import datetime
import os

bp = Blueprint('backups', __name__)
backup_service = BackupService()
drive_service = GoogleDriveService()

@bp.route('/')
def index():
    """Página principal de backups"""
    # Verificar si necesita configuración inicial
    needs_setup = backup_service.needs_directory_setup()
    
    backups = backup_service.list_backups()
    drive_configured = drive_service.is_configured()
    next_backups = backup_scheduler.get_next_scheduled_backups()
    config = backup_service.get_config()
    
    return render_template('backups/index.html',
                         backups=backups,
                         drive_configured=drive_configured,
                         next_backups=next_backups,
                         needs_setup=needs_setup,
                         config=config)

@bp.route('/create', methods=['POST'])
def create_backup():
    """Crear un nuevo backup"""
    backup_type = request.form.get('backup_type', 'local')
    
    result = backup_service.create_backup(backup_type)
    
    if result['success']:
        flash(f'Backup creado exitosamente: {result["backup_name"]}', 'success')
    else:
        flash(f'Error al crear backup: {result["error"]}', 'error')
    
    return redirect(url_for('backups.index'))

@bp.route('/api/create', methods=['POST'])
def api_create_backup():
    """API para crear backup"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No data received'}), 400
            
        backup_type = data.get('backup_type', 'local')
        custom_directory = data.get('custom_directory')
        
        # Si se especifica directorio personalizado, configurarlo
        if custom_directory and backup_type == 'local':
            config_result = backup_service.set_custom_directory(custom_directory)
            if not config_result['success']:
                return jsonify({
                    'success': False,
                    'error': config_result['error']
                }), 400
        
        result = backup_service.create_backup(backup_type)
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/api/select-directory', methods=['POST'])
def select_directory():
    """Abrir diálogo para seleccionar directorio personalizado"""
    try:
        import tkinter as tk
        from tkinter import filedialog
        
        # Crear ventana temporal para el diálogo
        root = tk.Tk()
        root.withdraw()  # Ocultar ventana principal
        root.attributes('-topmost', True)  # Traer al frente
        
        # Abrir diálogo de selección de carpeta
        directory = filedialog.askdirectory(
            title="Seleccionar directorio para backups",
            initialdir=os.path.expanduser("~")
        )
        
        root.destroy()  # Cerrar ventana temporal
        
        if directory:
            # Verificar que el directorio sea válido
            if os.path.exists(directory) and os.access(directory, os.W_OK):
                return jsonify({
                    'success': True,
                    'directory': directory
                })
            else:
                return jsonify({
                    'success': False,
                    'error': 'El directorio seleccionado no es válido o no tiene permisos de escritura'
                }), 400
        else:
            return jsonify({
                'success': False,
                'error': 'No se seleccionó ningún directorio'
            }), 400
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Error al seleccionar directorio: {str(e)}'
        }), 500

@bp.route('/api/config/directory', methods=['GET', 'POST'])
def get_directory_config():
    """Configurar directorio personalizado"""
    if request.method == 'POST':
        try:
            data = request.get_json()
            directory = data.get('directory')
            if not directory:
                return jsonify({
                    'success': False,
                    'error': 'Directorio requerido'
                }), 400
            
            result = backup_service.set_custom_directory(directory)
            return jsonify(result)
            
        except Exception as e:
            return jsonify({
                'success': False,
                'error': f'Error configurando directorio: {str(e)}'
            }), 500
    
    # GET: Obtener configuración actual
    try:
        config = backup_service.get_config()
        return jsonify({
            'success': True,
            'custom_directory': config.get('custom_directory'),
            'use_custom_directory': config.get('use_custom_directory', False)
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Error obteniendo configuración: {str(e)}'
        }), 500

@bp.route('/api/config/directory', methods=['POST'])
def config_directory():
    """Configurar directorio personalizado (POST)"""
    try:
        data = request.get_json()
        directory = data.get('directory')
        if not directory:
            return jsonify({
                'success': False,
                'error': 'Directorio requerido'
            }), 400
        
        result = backup_service.set_custom_directory(directory)
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Error configurando directorio: {str(e)}'
        }), 500

@bp.route('/api/setup/initial', methods=['POST'])
def initial_setup():
    """Configuración inicial de directorio"""
    try:
        result = backup_service.prompt_directory_setup()
        return jsonify(result)
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Error en configuración inicial: {str(e)}'
        }), 500

@bp.route('/api/setup/check', methods=['GET'])
def check_setup():
    """Verificar si necesita configuración inicial"""
    try:
        needs_setup = backup_service.needs_directory_setup()
        config = backup_service.get_config()
        return jsonify({
            'success': True,
            'needs_setup': needs_setup,
            'config': config
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@bp.route('/list')
def list_backups():
    """API para listar backups"""
    backup_type = request.args.get('type', 'all')
    backups = backup_service.list_backups(backup_type)
    return jsonify(backups)

@bp.route('/download/<path:backup_name>')
def download_backup(backup_name):
    """Descargar un backup"""
    try:
        # Buscar el archivo en ambos directorios usando rutas absolutas
        import os
        from pathlib import Path
        
        base_dir = Path(os.getcwd())
        local_path = base_dir / "backups" / "local" / f"{backup_name}.zip"
        cloud_path = base_dir / "backups" / "cloud" / f"{backup_name}.zip"
        
        if local_path.exists():
            return send_file(str(local_path), as_attachment=True)
        elif cloud_path.exists():
            return send_file(str(cloud_path), as_attachment=True)
        else:
            flash('Archivo de backup no encontrado', 'error')
            return redirect(url_for('backups.index'))
    except Exception as e:
        flash(f'Error al descargar backup: {str(e)}', 'error')
        return redirect(url_for('backups.index'))

@bp.route('/restore', methods=['POST'])
def restore_backup():
    """Restaurar un backup"""
    backup_path = request.form.get('backup_path')
    
    if not backup_path:
        flash('Debe seleccionar un backup para restaurar', 'error')
        return redirect(url_for('backups.index'))
    
    result = backup_service.restore_backup(backup_path)
    
    if result['success']:
        flash('Backup restaurado exitosamente. Se creó un backup de seguridad.', 'success')
    else:
        flash(f'Error al restaurar backup: {result["error"]}', 'error')
    
    return redirect(url_for('backups.index'))

@bp.route('/config')
def config():
    """Página de configuración de backups"""
    drive_configured = drive_service.is_configured()
    setup_instructions = drive_service.get_setup_instructions()
    return render_template('backups/config.html',
                         drive_configured=drive_configured,
                         setup_instructions=setup_instructions)

@bp.route('/config/google-drive', methods=['POST'])
def setup_google_drive():
    """Configurar credenciales de Google Drive"""
    try:
        # Verificar si se subió un archivo
        if 'credentials_file' in request.files:
            file = request.files['credentials_file']
            if file.filename != '':
                credentials_content = file.read().decode('utf-8')
            else:
                credentials_content = request.form.get('credentials')
        else:
            credentials_content = request.form.get('credentials')
        
        if not credentials_content:
            flash('Debe proporcionar las credenciales de Google Drive', 'error')
            return redirect(url_for('backups.config'))
        
        result = drive_service.setup_credentials(credentials_content)
        
        if result['success']:
            flash('Google Drive configurado correctamente', 'success')
        else:
            flash(f'Error configurando Google Drive: {result["error"]}', 'error')
        
    except Exception as e:
        flash(f'Error procesando credenciales: {str(e)}', 'error')
    
    return redirect(url_for('backups.config'))

@bp.route('/scheduler/start', methods=['POST'])
def start_scheduler():
    """Iniciar scheduler de backups automáticos"""
    backup_scheduler.start()
    flash('Scheduler de backups automáticos iniciado', 'success')
    return redirect(url_for('backups.index'))

@bp.route('/scheduler/stop', methods=['POST'])
def stop_scheduler():
    """Detener scheduler de backups automáticos"""
    backup_scheduler.stop()
    flash('Scheduler de backups automáticos detenido', 'warning')
    return redirect(url_for('backups.index'))

@bp.route('/force-backup', methods=['POST'])
def force_backup():
    """Forzar ejecución de backup programado"""
    backup_type = request.form.get('backup_type', 'local')
    
    result = backup_scheduler.force_backup(backup_type)
    
    if result and result.get('success'):
        flash(f'Backup {backup_type} ejecutado exitosamente', 'success')
    else:
        error_msg = result.get('error', 'Error desconocido') if result else 'Error ejecutando backup'
        flash(f'Error ejecutando backup: {error_msg}', 'error')
    
    return redirect(url_for('backups.index'))

@bp.route('/delete', methods=['POST'])
def delete_backup():
    """Eliminar un backup"""
    backup_path = request.form.get('backup_path')
    
    try:
        if os.path.exists(backup_path):
            os.remove(backup_path)
            flash('Backup eliminado exitosamente', 'success')
        else:
            flash('Archivo de backup no encontrado', 'error')
    except Exception as e:
        flash(f'Error al eliminar backup: {str(e)}', 'error')
    
    return redirect(url_for('backups.index'))

@bp.route('/cleanup', methods=['POST'])
def cleanup_backups():
    """Limpiar backups antiguos"""
    try:
        backup_service.cleanup_old_backups()
        flash('Limpieza de backups completada', 'success')
    except Exception as e:
        flash(f'Error en limpieza: {str(e)}', 'error')
    
    return redirect(url_for('backups.index'))

@bp.route('/config/google-drive/reset', methods=['POST'])
def reset_google_drive():
    """Resetear configuración de Google Drive"""
    try:
        result = drive_service.reset_credentials()
        if result['success']:
            return jsonify({'success': True, 'message': 'Configuración reseteada'})
        else:
            return jsonify({'success': False, 'error': result['error']}), 400
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/config/google-drive/test', methods=['POST'])
def test_google_drive():
    """Probar conexión con Google Drive"""
    try:
        result = drive_service.test_connection()
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/config/reset', methods=['POST'])
def reset_all_config():
    """Resetear toda la configuración de backups"""
    try:
        backup_service = BackupService()
        drive_service = GoogleDriveService()
        
        # Resetear configuración de backups
        backup_result = backup_service.reset_config()
        if not backup_result['success']:
            return jsonify(backup_result), 500
        
        # Resetear configuración de Google Drive
        drive_result = drive_service.reset_credentials()
        if not drive_result['success']:
            return jsonify(drive_result), 500
        
        return jsonify({
            'success': True,
            'message': 'Toda la configuración ha sido reseteada correctamente'
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/clear-cache', methods=['POST'])
def clear_backup_cache():
    """Limpiar cache de backups"""
    try:
        backup_service = BackupService()
        result = backup_service.clear_all_backups()
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/api/schedule/config', methods=['GET'])
def get_schedule_config():
    """Obtener configuración de horarios de backups"""
    try:
        config = backup_scheduler.get_schedule_config()
        return jsonify({
            'success': True,
            'config': config
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/api/schedule/config', methods=['POST'])
def update_schedule_config():
    """Actualizar configuración de horarios de backups"""
    try:
        data = request.get_json()
        backup_type = data.get('backup_type')
        config = data.get('config')
        
        if not backup_type or not config:
            return jsonify({
                'success': False,
                'error': 'Tipo de backup y configuración requeridos'
            }), 400
        
        result = backup_scheduler.update_schedule_config(backup_type, config)
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/api/schedule/next', methods=['GET'])
def get_next_backups():
    """Obtener próximos backups programados"""
    try:
        next_backups = backup_scheduler.get_next_scheduled_backups()
        return jsonify({
            'success': True,
            'next_backups': next_backups
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500