from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from app.services import InstrumentoService

bp = Blueprint('instrumentos', __name__)
instrumento_service = InstrumentoService()

@bp.route('/')
@login_required
def listar_instrumentos():
    """Lista todos los instrumentos"""
    instrumentos = instrumento_service.obtener_todos()
    return render_template('instrumentos/list.html', instrumentos=instrumentos)

@bp.route('/nuevo', methods=['GET', 'POST'])
def nuevo_instrumento():
    """Crear un nuevo instrumento"""
    if request.method == 'POST':
        try:
            codigo = request.form['codigo']
            nombre = request.form['nombre']
            marca = request.form['marca']
            modelo = request.form['modelo']
            serie = request.form['serie']
            estado = request.form['estado']
            valor_unitario = float(request.form.get('valor_unitario', 0))
            
            instrumento_service.crear_instrumento(
                codigo, nombre, marca, modelo, serie, estado, valor_unitario
            )
            
            flash('Instrumento creado exitosamente', 'success')
            return redirect(url_for('instrumentos.listar_instrumentos'))
        except Exception as e:
            flash(f'Error al crear instrumento: {str(e)}', 'error')
    
    return render_template('instrumentos/form.html')

@bp.route('/<int:instrumento_id>')
def detalle_instrumento(instrumento_id):
    """Ver detalles de un instrumento"""
    instrumento = instrumento_service.obtener_por_id(instrumento_id)
    if not instrumento:
        flash('Instrumento no encontrado', 'error')
        return redirect(url_for('instrumentos.listar_instrumentos'))
    
    movimientos = instrumento_service.obtener_movimientos(instrumento.i_id)
    
    return render_template('instrumentos/detail.html',
                         instrumento=instrumento, movimientos=movimientos)

@bp.route('/<int:instrumento_id>/editar', methods=['GET', 'POST'])
def editar_instrumento(instrumento_id):
    """Editar un instrumento"""
    instrumento = instrumento_service.obtener_por_id(instrumento_id)
    if not instrumento:
        flash('Instrumento no encontrado', 'error')
        return redirect(url_for('instrumentos.listar_instrumentos'))
    
    if request.method == 'POST':
        try:
            instrumento_service.actualizar_instrumento(
                instrumento_id,
                marca=request.form['marca'],
                modelo=request.form['modelo'],
                serie=request.form['serie'],
                estado=request.form['estado']
            )
            
            flash('Instrumento actualizado exitosamente', 'success')
            return redirect(url_for('instrumentos.detalle_instrumento', instrumento_id=instrumento_id))
        except Exception as e:
            flash(f'Error al actualizar instrumento: {str(e)}', 'error')
    
    return render_template('instrumentos/form.html', instrumento=instrumento)

@bp.route('/<int:instrumento_id>/eliminar', methods=['POST'])
def eliminar_instrumento(instrumento_id):
    """Eliminar un instrumento"""
    try:
        if instrumento_service.eliminar_instrumento(instrumento_id):
            flash('Instrumento eliminado exitosamente', 'success')
        else:
            flash('No se pudo eliminar el instrumento', 'error')
    except Exception as e:
        flash(f'Error al eliminar instrumento: {str(e)}', 'error')
    
    return redirect(url_for('instrumentos.listar_instrumentos'))

@bp.route('/<int:instrumento_id>/cambiar-estado', methods=['POST'])
def cambiar_estado(instrumento_id):
    """Cambiar el estado de un instrumento"""
    try:
        nuevo_estado = request.form['estado']
        instrumento_service.actualizar_estado(instrumento_id, nuevo_estado)
        flash('Estado actualizado exitosamente', 'success')
    except Exception as e:
        flash(f'Error al cambiar estado: {str(e)}', 'error')
    
    return redirect(request.referrer or url_for('instrumentos.listar_instrumentos'))