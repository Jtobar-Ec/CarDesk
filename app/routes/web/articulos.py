from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app.services import ArticuloService

bp = Blueprint('articulos', __name__)
articulo_service = ArticuloService()

@bp.route('/')
@login_required
def listar_articulos():
    """Lista todos los artículos"""
    articulos = articulo_service.obtener_todos()
    return render_template('articulos/list.html', articulos=articulos)

@bp.route('/nuevo', methods=['GET', 'POST'])
@login_required
def nuevo_articulo():
    """Crear un nuevo artículo"""
    if request.method == 'POST':
        try:
            codigo = request.form['codigo']
            nombre = request.form['nombre']
            cantidad = int(request.form['cantidad'])
            valor_unitario = float(request.form['valor_unitario'])
            cuenta_contable = request.form['cuenta_contable']
            stock_min = int(request.form.get('stock_min', 0))
            stock_max = int(request.form.get('stock_max', 100))
            
            articulo_service.crear_articulo(
                codigo, nombre, cantidad, valor_unitario, 
                cuenta_contable, stock_min, stock_max
            )
            
            flash('Artículo creado exitosamente', 'success')
            return redirect(url_for('articulos.listar_articulos'))
        except Exception as e:
            flash(f'Error al crear artículo: {str(e)}', 'error')
    
    return render_template('articulos/form.html')

@bp.route('/<codigo>')
@login_required
def detalle_articulo(codigo):
    """Ver detalles de un artículo"""
    resultado = articulo_service.obtener_por_codigo(codigo)
    if not resultado:
        flash('Artículo no encontrado', 'error')
        return redirect(url_for('articulos.listar_articulos'))
    
    articulo, item = resultado
    movimientos = articulo_service.obtener_movimientos(item.id)
    
    return render_template('articulos/detail.html', 
                         articulo=articulo, item=item, movimientos=movimientos)

@bp.route('/stock-bajo')
@login_required
def stock_bajo():
    """Lista artículos con stock bajo"""
    articulos = articulo_service.obtener_stock_bajo()
    return render_template('articulos/stock_bajo.html', articulos=articulos)

@bp.route('/<int:articulo_id>/entrada', methods=['POST'])
@login_required
def registrar_entrada(articulo_id):
    """Registra una entrada de artículo"""
    try:
        cantidad = int(request.form['cantidad'])
        valor_unitario = float(request.form['valor_unitario'])
        observaciones = request.form.get('observaciones')
        usuario_id = current_user.id
        
        articulo_service.registrar_entrada(
            articulo_id, cantidad, valor_unitario, usuario_id, observaciones
        )
        
        flash('Entrada registrada exitosamente', 'success')
    except Exception as e:
        flash(f'Error al registrar entrada: {str(e)}', 'error')
    
    return redirect(request.referrer or url_for('articulos.listar_articulos'))

@bp.route('/<int:articulo_id>/salida', methods=['POST'])
@login_required
def registrar_salida(articulo_id):
    """Registra una salida de artículo"""
    try:
        cantidad = int(request.form['cantidad'])
        valor_unitario = float(request.form['valor_unitario'])
        observaciones = request.form.get('observaciones')
        usuario_id = current_user.id
        
        articulo_service.registrar_salida(
            articulo_id, cantidad, valor_unitario, usuario_id, observaciones
        )
        
        flash('Salida registrada exitosamente', 'success')
    except ValueError as e:
        flash(str(e), 'error')
    except Exception as e:
        flash(f'Error al registrar salida: {str(e)}', 'error')
    
    return redirect(request.referrer or url_for('articulos.listar_articulos'))