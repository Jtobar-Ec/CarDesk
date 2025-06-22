from flask import Blueprint, render_template, request, redirect, url_for, flash
from app.services import ProveedorService

bp = Blueprint('proveedores', __name__)
proveedor_service = ProveedorService()

@bp.route('/')
def listar_proveedores():
    """Lista todos los proveedores"""
    proveedores = proveedor_service.obtener_todos()
    return render_template('proveedores/list.html', proveedores=proveedores)

@bp.route('/nuevo', methods=['GET', 'POST'])
def nuevo_proveedor():
    """Crear un nuevo proveedor"""
    if request.method == 'POST':
        try:
            codigo = request.form['codigo']
            razon_social = request.form['razon_social']
            ci_ruc = request.form['ci_ruc']
            direccion = request.form.get('direccion')
            telefono = request.form.get('telefono')
            correo = request.form.get('correo')
            
            proveedor_service.crear_proveedor(
                codigo, razon_social, ci_ruc, direccion, telefono, correo
            )
            
            flash('Proveedor creado exitosamente', 'success')
            return redirect(url_for('proveedores.listar_proveedores'))
        except Exception as e:
            flash(f'Error al crear proveedor: {str(e)}', 'error')
    
    return render_template('proveedores/form.html')

@bp.route('/<int:proveedor_id>')
def detalle_proveedor(proveedor_id):
    """Ver detalles de un proveedor"""
    proveedor = proveedor_service.obtener_por_id(proveedor_id)
    if not proveedor:
        flash('Proveedor no encontrado', 'error')
        return redirect(url_for('proveedores.listar_proveedores'))
    
    return render_template('proveedores/detail.html', proveedor=proveedor)

@bp.route('/<int:proveedor_id>/editar', methods=['GET', 'POST'])
def editar_proveedor(proveedor_id):
    """Editar un proveedor"""
    proveedor = proveedor_service.obtener_por_id(proveedor_id)
    if not proveedor:
        flash('Proveedor no encontrado', 'error')
        return redirect(url_for('proveedores.listar_proveedores'))
    
    if request.method == 'POST':
        try:
            datos = {
                'p_codigo': request.form['codigo'],
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
def buscar_proveedores():
    """Buscar proveedores por nombre"""
    nombre = request.args.get('nombre', '')
    proveedores = []
    
    if nombre:
        proveedores = proveedor_service.buscar_por_nombre(nombre)
    
    return render_template('proveedores/search.html', proveedores=proveedores, nombre=nombre)