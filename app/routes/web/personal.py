from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required
from app.services.personal_service import PersonalService
from datetime import date

bp = Blueprint('personal', __name__)
personal_service = PersonalService()

@bp.route('/')
@login_required
def listar_personal():
    """Lista todo el personal"""
    personal = personal_service.obtener_todos()
    return render_template('personal/list.html', personal=personal)

@bp.route('/nuevo', methods=['GET', 'POST'])
@login_required
def nuevo_personal():
    """Crear una nueva persona"""
    if request.method == 'POST':
        try:
            nombre = request.form['nombre']
            apellido = request.form['apellido']
            ci = request.form['ci']
            telefono = request.form.get('telefono')
            correo = request.form.get('correo')
            direccion = request.form.get('direccion')
            cargo = request.form.get('cargo')
            estado = request.form.get('estado', 'Activo')
            
            personal_service.crear_persona(
                nombre=nombre,
                apellido=apellido,
                ci=ci,
                telefono=telefono,
                correo=correo,
                direccion=direccion,
                cargo=cargo,
                estado=estado
            )
            
            flash('Persona creada exitosamente', 'success')
            return redirect(url_for('personal.listar_personal'))
        except Exception as e:
            flash(f'Error al crear persona: {str(e)}', 'error')
    
    # Obtener opciones para los selects
    cargos = personal_service.obtener_cargos_disponibles()
    estados = personal_service.obtener_estados_disponibles()
    return render_template('personal/form.html', cargos=cargos, estados=estados)

@bp.route('/<int:persona_id>')
@login_required
def detalle_personal(persona_id):
    """Ver detalles de una persona"""
    persona = personal_service.obtener_por_id(persona_id)
    if not persona:
        flash('Persona no encontrada', 'error')
        return redirect(url_for('personal.listar_personal'))
    
    # Obtener historial de consumos
    consumos = personal_service.obtener_historial_consumos(persona_id)
    
    today = date.today().strftime('%Y-%m-%d')
    return render_template('personal/detail.html', persona=persona, consumos=consumos, today=today)

@bp.route('/<int:persona_id>/editar', methods=['GET', 'POST'])
@login_required
def editar_personal(persona_id):
    """Editar una persona"""
    persona = personal_service.obtener_por_id(persona_id)
    if not persona:
        flash('Persona no encontrada', 'error')
        return redirect(url_for('personal.listar_personal'))
    
    if request.method == 'POST':
        try:
            # Obtener todos los campos del formulario
            datos = {
                'nombre': request.form['nombre'],
                'apellido': request.form.get('apellido', ''),
                'ci': request.form.get('ci', ''),
                'telefono': request.form.get('telefono', ''),
                'correo': request.form.get('correo', ''),
                'direccion': request.form.get('direccion', ''),
                'cargo': request.form.get('cargo', ''),
                'estado': request.form.get('estado', 'Activo')
            }
            
            personal_service.actualizar_persona(persona_id, **datos)
            flash('Persona actualizada exitosamente', 'success')
            return redirect(url_for('personal.detalle_personal', persona_id=persona_id))
        except Exception as e:
            flash(f'Error al actualizar persona: {str(e)}', 'error')
    
    # Obtener opciones para los selects
    cargos = personal_service.obtener_cargos_disponibles()
    estados = personal_service.obtener_estados_disponibles()
    return render_template('personal/form.html', persona=persona, cargos=cargos, estados=estados)

@bp.route('/<int:persona_id>/eliminar', methods=['POST'])
@login_required
def eliminar_personal(persona_id):
    """Eliminar una persona"""
    try:
        if personal_service.eliminar_persona(persona_id):
            flash('Persona eliminada exitosamente', 'success')
        else:
            flash('No se pudo eliminar la persona', 'error')
    except Exception as e:
        flash(f'Error al eliminar persona: {str(e)}', 'error')
    
    return redirect(url_for('personal.listar_personal'))

@bp.route('/<int:persona_id>/cambiar-estado', methods=['POST'])
@login_required
def cambiar_estado(persona_id):
    """Cambiar el estado de una persona"""
    try:
        nuevo_estado = request.form['estado']
        personal_service.cambiar_estado(persona_id, nuevo_estado)
        flash(f'Estado cambiado a {nuevo_estado} exitosamente', 'success')
    except Exception as e:
        flash(f'Error al cambiar estado: {str(e)}', 'error')
    
    return redirect(request.referrer or url_for('personal.listar_personal'))

@bp.route('/buscar')
@login_required
def buscar_personal():
    """Buscar personal por nombre, apellido o código"""
    termino = request.args.get('termino', '').strip()
    personal = []
    
    if termino:
        personal = personal_service.buscar_por_nombre(termino)
    
    return render_template('personal/search.html', personal=personal, termino=termino)

@bp.route('/activos')
@login_required
def personal_activo():
    """Lista solo el personal activo"""
    personal = personal_service.obtener_activos()
    return render_template('personal/list.html', personal=personal, titulo="Personal Activo")

@bp.route('/por-cargo/<cargo>')
@login_required
def personal_por_cargo(cargo):
    """Lista personal por cargo"""
    personal = personal_service.obtener_por_cargo(cargo)
    return render_template('personal/list.html', personal=personal, titulo=f"Personal - {cargo}")

@bp.route('/api/activos')
@login_required
def api_personal_activo():
    """API endpoint para obtener personal activo en formato JSON"""
    try:
        personal = personal_service.obtener_activos()
        personal_data = []
        
        for persona in personal:
            personal_data.append({
                'id': persona.id,
                'nombre': persona.pe_nombre,
                'apellido': persona.pe_apellido or '',
                'ci': persona.pe_ci or '',
                'telefono': persona.pe_telefono or '',
                'correo': persona.pe_correo or '',
                'direccion': persona.pe_direccion or '',
                'cargo': persona.pe_cargo or '',
                'estado': persona.pe_estado
            })
        
        return jsonify({
            'success': True,
            'personal': personal_data,
            'total': len(personal_data)
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'personal': []
        }), 500