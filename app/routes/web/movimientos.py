from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from app.services import InstrumentoService
from app.database.models import Usuario
from app.database import db

bp = Blueprint('movimientos', __name__)
instrumento_service = InstrumentoService()

@bp.route('/instrumento/<int:instrumento_id>/entrada', methods=['GET', 'POST'])
def registrar_entrada(instrumento_id):
    """Registrar una entrada de instrumento"""
    instrumento = instrumento_service.obtener_por_id(instrumento_id)
    if not instrumento:
        flash('Instrumento no encontrado', 'error')
        return redirect(url_for('instrumentos.listar_instrumentos'))
    
    if request.method == 'POST':
        try:
            cantidad = int(request.form['cantidad'])
            valor_unitario = float(request.form['valor_unitario'])
            observaciones = request.form.get('observaciones', '').strip()
            
            # Por ahora usar el primer usuario disponible
            # En una implementación real, esto vendría de la sesión del usuario autenticado
            usuario = Usuario.query.first()
            if not usuario:
                flash('No hay usuarios registrados en el sistema', 'error')
                return redirect(url_for('instrumentos.detalle_instrumento', instrumento_id=instrumento_id))
            
            movimiento = instrumento_service.registrar_entrada(
                instrumento_id, cantidad, valor_unitario, usuario.id, observaciones
            )
            
            flash(f'Entrada registrada exitosamente. Movimiento ID: {movimiento.id}', 'success')
            return redirect(url_for('instrumentos.detalle_instrumento', instrumento_id=instrumento_id))
            
        except ValueError as e:
            flash(f'Error en los datos: {str(e)}', 'error')
        except Exception as e:
            flash(f'Error al registrar entrada: {str(e)}', 'error')
    
    return render_template('movimientos/entrada_form.html', instrumento=instrumento)

@bp.route('/instrumento/<int:instrumento_id>/salida', methods=['GET', 'POST'])
def registrar_salida(instrumento_id):
    """Registrar una salida de instrumento"""
    instrumento = instrumento_service.obtener_por_id(instrumento_id)
    if not instrumento:
        flash('Instrumento no encontrado', 'error')
        return redirect(url_for('instrumentos.listar_instrumentos'))
    
    if request.method == 'POST':
        try:
            cantidad = int(request.form['cantidad'])
            valor_unitario = float(request.form['valor_unitario'])
            observaciones = request.form.get('observaciones', '').strip()
            
            # Por ahora usar el primer usuario disponible
            usuario = Usuario.query.first()
            if not usuario:
                flash('No hay usuarios registrados en el sistema', 'error')
                return redirect(url_for('instrumentos.detalle_instrumento', instrumento_id=instrumento_id))
            
            movimiento = instrumento_service.registrar_salida(
                instrumento_id, cantidad, valor_unitario, usuario.id, observaciones
            )
            
            flash(f'Salida registrada exitosamente. Movimiento ID: {movimiento.id}', 'success')
            return redirect(url_for('instrumentos.detalle_instrumento', instrumento_id=instrumento_id))
            
        except ValueError as e:
            flash(f'Error: {str(e)}', 'error')
        except Exception as e:
            flash(f'Error al registrar salida: {str(e)}', 'error')
    
    return render_template('movimientos/salida_form.html', instrumento=instrumento)

@bp.route('/instrumento/<int:instrumento_id>/movimientos')
def historial_movimientos(instrumento_id):
    """Ver historial completo de movimientos de un instrumento"""
    instrumento = instrumento_service.obtener_por_id(instrumento_id)
    if not instrumento:
        flash('Instrumento no encontrado', 'error')
        return redirect(url_for('instrumentos.listar_instrumentos'))
    
    movimientos = instrumento_service.obtener_movimientos(instrumento.i_id)
    
    return render_template('movimientos/historial.html', 
                         instrumento=instrumento, 
                         movimientos=movimientos)

@bp.route('/api/instrumento/<int:instrumento_id>/stock')
def obtener_stock_actual(instrumento_id):
    """API para obtener el stock actual de un instrumento"""
    try:
        instrumento = instrumento_service.obtener_por_id(instrumento_id)
        if not instrumento:
            return jsonify({'error': 'Instrumento no encontrado'}), 404
        
        return jsonify({
            'instrumento_id': instrumento_id,
            'stock_actual': instrumento.item.i_cantidad if instrumento.item else 0,
            'valor_unitario': float(instrumento.item.i_vUnitario) if instrumento.item else 0.0,
            'valor_total': float(instrumento.item.i_vTotal) if instrumento.item else 0.0
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500