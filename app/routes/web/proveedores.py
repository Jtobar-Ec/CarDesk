from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required
from app.services import ProveedorService


bp = Blueprint('proveedores', __name__)
proveedor_service = ProveedorService()

@bp.route('/')
@login_required
def listar_proveedores():
    """Lista todos los proveedores"""
    incluir_inactivos = request.args.get('incluir_inactivos', 'true').lower() == 'true'
    proveedores = proveedor_service.obtener_todos(incluir_inactivos=incluir_inactivos)
    return render_template('proveedores/list.html', proveedores=proveedores, incluir_inactivos=incluir_inactivos)

@bp.route('/nuevo', methods=['GET', 'POST'])
@login_required
def nuevo_proveedor():
    """Crear un nuevo proveedor"""
    if request.method == 'POST':
        try:
            razon_social = request.form['razon_social']
            ci_ruc = request.form['ci_ruc']
            direccion = request.form.get('direccion')
            telefono = request.form.get('telefono')
            correo = request.form.get('correo')
            
            proveedor_service.crear_proveedor(
                razon_social, ci_ruc, direccion, telefono, correo
            )
            
            flash('Proveedor creado exitosamente', 'success')
            return redirect(url_for('proveedores.listar_proveedores'))
        except Exception as e:
            flash(f'Error al crear proveedor: {str(e)}', 'error')
    
    return render_template('proveedores/form.html')

@bp.route('/<int:proveedor_id>')
@login_required
def detalle_proveedor(proveedor_id):
    """Ver detalles de un proveedor"""
    from datetime import date
    
    proveedor = proveedor_service.obtener_por_id(proveedor_id)
    if not proveedor:
        flash('Proveedor no encontrado', 'error')
        return redirect(url_for('proveedores.listar_proveedores'))
    
    today = date.today().strftime('%Y-%m-%d')
    return render_template('proveedores/detail.html', proveedor=proveedor, today=today)

@bp.route('/<int:proveedor_id>/editar', methods=['GET', 'POST'])
@login_required
def editar_proveedor(proveedor_id):
    """Editar un proveedor"""
    proveedor = proveedor_service.obtener_por_id(proveedor_id)
    if not proveedor:
        flash('Proveedor no encontrado', 'error')
        return redirect(url_for('proveedores.listar_proveedores'))
    
    if request.method == 'POST':
        try:
            datos = {
                'p_razonsocial': request.form['razon_social'],
                'p_ci_ruc': request.form['ci_ruc'],
                'p_direccion': request.form.get('direccion'),
                'p_telefono': request.form.get('telefono'),
                'p_correo': request.form.get('correo')
            }
            
            proveedor_service.actualizar_proveedor(proveedor_id, **datos)
            flash('Proveedor actualizado exitosamente', 'success')
            return redirect(url_for('proveedores.detalle_proveedor', proveedor_id=proveedor_id))
        except Exception as e:
            flash(f'Error al actualizar proveedor: {str(e)}', 'error')
    
    return render_template('proveedores/form.html', proveedor=proveedor)

@bp.route('/buscar')
@login_required
def buscar_proveedores():
    """Buscar proveedores por nombre"""
    nombre = request.args.get('nombre', '').strip()
    proveedores = []
    
    # Solo buscar si hay un término de búsqueda válido
    if nombre and len(nombre) >= 2:
        proveedores = proveedor_service.buscar_por_nombre(nombre)
    elif nombre and len(nombre) < 2:
        # Si el término es muy corto, mostrar mensaje de error
        flash('El término de búsqueda debe tener al menos 2 caracteres', 'warning')
    
    return render_template('proveedores/search.html', proveedores=proveedores, nombre=nombre)

@bp.route('/<int:proveedor_id>/cambiar-estado', methods=['POST'])
@login_required
def cambiar_estado_proveedor(proveedor_id):
    """Cambiar estado de un proveedor (Activo/Inactivo)"""
    try:
        nuevo_estado = request.form.get('nuevo_estado')
        
        # Verificar si el nuevo estado es válido
        if nuevo_estado not in ['Activo', 'Inactivo']:
            flash('Estado no válido', 'error')
            return redirect(url_for('proveedores.listar_proveedores'))
        
        print(f"Cambiando estado del proveedor {proveedor_id} a {nuevo_estado}")
        
        # Llamar al servicio para cambiar el estado
        if proveedor_service.cambiar_estado_proveedor(proveedor_id, nuevo_estado):
            accion = 'activado' if nuevo_estado == 'Activo' else 'desactivado'
            flash(f'Proveedor {accion} exitosamente', 'success')
        else:
            flash('No se pudo cambiar el estado del proveedor', 'error')
    except Exception as e:
        flash(f'Error al cambiar estado: {str(e)}', 'error')
    
    return redirect(url_for('proveedores.listar_proveedores'))

@bp.route('/<int:proveedor_id>/eliminar', methods=['POST'])
@login_required
def eliminar_proveedor(proveedor_id):
    """Desactivar un proveedor (mantener por compatibilidad)"""
    try:
        if proveedor_service.desactivar_proveedor(proveedor_id):
            flash('Proveedor desactivado exitosamente', 'success')
        else:
            flash('No se pudo desactivar el proveedor', 'error')
    except Exception as e:
        flash(f'Error al desactivar proveedor: {str(e)}', 'error')
    
    return redirect(url_for('proveedores.listar_proveedores'))

@bp.route('/crear-ajax', methods=['POST'])
@login_required
def crear_proveedor_ajax():
    """Crear un nuevo proveedor vía AJAX"""
    try:
        razon_social = request.form['razon_social']
        ci_ruc = request.form['ci_ruc']
        direccion = request.form.get('direccion')
        telefono = request.form.get('telefono')
        correo = request.form.get('correo')
        
        proveedor = proveedor_service.crear_proveedor(
            razon_social, ci_ruc, direccion, telefono, correo
        )
        
        return jsonify({
            'success': True,
            'proveedor': {
                'id': proveedor.id,
                'p_codigo': proveedor.p_codigo,
                'p_razonsocial': proveedor.p_razonsocial
            }
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error al crear proveedor: {str(e)}'
        })