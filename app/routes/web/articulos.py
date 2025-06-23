from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app.services import ArticuloService
from app.services.proveedor_service import ProveedorService

bp = Blueprint('articulos', __name__)
articulo_service = ArticuloService()
proveedor_service = ProveedorService()

@bp.route('/')
@login_required
def listar_articulos():
    """Lista todos los artículos"""
    articulos = articulo_service.obtener_todos_articulos()
    return render_template('articulos/list.html', articulos=articulos)

@bp.route('/nuevo', methods=['GET', 'POST'])
@login_required
def nuevo_articulo():
    """Crear un nuevo artículo"""
    if request.method == 'POST':
        try:
            nombre = request.form['nombre']
            cantidad = int(request.form['cantidad'])
            valor_unitario = float(request.form['valor_unitario'])
            cuenta_contable = request.form['cuenta_contable']
            stock_min = int(request.form.get('stock_min', 0))
            stock_max = int(request.form.get('stock_max', 100))
            proveedor_id = request.form.get('proveedor_id')
            
            # Convertir proveedor_id a int si existe
            if proveedor_id and proveedor_id.strip():
                proveedor_id = int(proveedor_id)
            else:
                proveedor_id = None
            
            articulo, item = articulo_service.crear_articulo(
                nombre=nombre,
                cantidad=cantidad,
                valor_unitario=valor_unitario,
                cuenta_contable=cuenta_contable,
                stock_min=stock_min,
                stock_max=stock_max,
                usuario_id=current_user.id
            )
            
            # Si se especificó un proveedor, registrar la entrada inicial
            if proveedor_id and cantidad > 0:
                articulo_service.registrar_entrada(
                    articulo.i_id, cantidad, valor_unitario, current_user.id,
                    proveedor_id=proveedor_id,
                    observaciones=f"Entrada inicial del artículo {item.i_codigo}"
                )
            
            flash('Artículo creado exitosamente', 'success')
            return redirect(url_for('articulos.listar_articulos'))
        except Exception as e:
            flash(f'Error al crear artículo: {str(e)}', 'error')
    
    # Obtener todos los proveedores para el formulario
    proveedores = proveedor_service.obtener_todos()
    return render_template('articulos/form.html', proveedores=proveedores)
@bp.route('/<int:articulo_id>/detalle')
@login_required
def detalle_articulo(articulo_id):
    """Ver detalles de un artículo"""
    resultado = articulo_service.obtener_articulo_por_id(articulo_id)
    if not resultado:
        flash('Artículo no encontrado', 'error')
        return redirect(url_for('articulos.listar_articulos'))
    
    articulo = resultado
    item = articulo.item
    
    # Obtener movimientos del historial
    from app.database.models import MovimientoDetalle
    from app import db
    movimientos = db.session.query(MovimientoDetalle).filter_by(
        i_id=item.id
    ).order_by(MovimientoDetalle.m_fecha.desc()).all()
    
    # Obtener todos los proveedores para el modal
    proveedores = proveedor_service.obtener_todos()
    
    return render_template('articulos/detail.html',
                         articulo=articulo, item=item, movimientos=movimientos,
                         proveedores=proveedores)

@bp.route('/buscar')
def buscar_articulos():
    """Busca artículos por nombre o código"""
    termino = request.args.get('q', '').strip()
    if termino:
        articulos = articulo_service.buscar_articulos(termino)
    else:
        articulos = articulo_service.obtener_todos_articulos()
    
    return render_template('articulos/list.html', articulos=articulos, termino_busqueda=termino)

@bp.route('/<int:articulo_id>/editar', methods=['GET', 'POST'])
def editar_articulo(articulo_id):
    """Editar un artículo"""
    resultado = articulo_service.obtener_articulo_por_id(articulo_id)
    if not resultado:
        flash('Artículo no encontrado', 'error')
        return redirect(url_for('articulos.listar_articulos'))
    
    # Obtener tanto el artículo como el item
    articulo = resultado
    item = articulo.item
    
    if request.method == 'POST':
        try:
            articulo_service.actualizar_articulo(
                articulo_id,
                nombre=request.form['nombre'],
                codigo=request.form['codigo'],
                cuenta_contable=request.form['cuenta_contable'],
                stock_min=int(request.form.get('stock_min', 0)),
                stock_max=int(request.form.get('stock_max', 100))
            )
            
            flash('Artículo actualizado exitosamente', 'success')
            return redirect(url_for('articulos.detalle_articulo', articulo_id=articulo_id))
        except Exception as e:
            flash(f'Error al actualizar artículo: {str(e)}', 'error')
    
    # Obtener todos los proveedores para el formulario (aunque no se use en edición)
    proveedores = proveedor_service.obtener_todos()
    return render_template('articulos/form.html', articulo=articulo, item=item, proveedores=proveedores)

@bp.route('/<int:articulo_id>/eliminar', methods=['POST'])
def eliminar_articulo(articulo_id):
    """Eliminar un artículo"""
    try:
        if articulo_service.eliminar_articulo(articulo_id):
            flash('Artículo eliminado exitosamente', 'success')
        else:
            flash('No se pudo eliminar el artículo', 'error')
    except Exception as e:
        flash(f'Error al eliminar artículo: {str(e)}', 'error')
    
    return redirect(url_for('articulos.listar_articulos'))

@bp.route('/<int:articulo_id>/actualizar-precio', methods=['POST'])
def actualizar_precio(articulo_id):
    """Actualiza el valor unitario de un artículo"""
    try:
        nuevo_valor = float(request.form['nuevo_valor'])
        observaciones = request.form.get('observaciones', '').strip()
        usuario_id = 1  # Por ahora usuario fijo
        
        articulo_service.actualizar_valor_unitario(
            articulo_id, nuevo_valor, usuario_id, observaciones
        )
        
        flash('Valor unitario actualizado exitosamente', 'success')
    except Exception as e:
        flash(f'Error al actualizar precio: {str(e)}', 'error')
    
    return redirect(request.referrer or url_for('articulos.listar_articulos'))

@bp.route('/stock-bajo')
@login_required
def stock_bajo():
    """Lista artículos con stock bajo"""
    articulos = articulo_service.obtener_articulos_stock_bajo()
    return render_template('articulos/stock_bajo.html', articulos=articulos)

@bp.route('/<int:articulo_id>/entrada', methods=['POST'])
@login_required
def registrar_entrada(articulo_id):
    """Registra una entrada de artículo"""
    try:
        cantidad = int(request.form['cantidad'])
        valor_unitario = float(request.form['valor_unitario'])
        proveedor_id = request.form.get('proveedor_id')
        observaciones = request.form.get('observaciones')
        usuario_id = current_user.id
        
        # Convertir proveedor_id a int si existe
        if proveedor_id and proveedor_id.strip():
            proveedor_id = int(proveedor_id)
        else:
            proveedor_id = None
        
        articulo_service.registrar_entrada(
            articulo_id, cantidad, valor_unitario, usuario_id,
            proveedor_id=proveedor_id, observaciones=observaciones
        )
        
        flash('Entrada registrada exitosamente', 'success')
    except Exception as e:
        flash(f'Error al registrar entrada: {str(e)}', 'error')
    
    return redirect(request.referrer or url_for('articulos.listar_articulos'))

@bp.route('/asignaciones')
@login_required
def listar_asignaciones():
    """Lista todas las asignaciones de artículos a personal"""
    from app.database.models import Consumo, Persona, Item
    from app import db
    
    # Obtener todas las asignaciones con información del personal y artículo
    asignaciones = db.session.query(Consumo, Persona, Item).join(
        Persona, Consumo.pe_id == Persona.id
    ).join(
        Item, Consumo.i_id == Item.id
    ).order_by(Consumo.c_fecha.desc(), Consumo.c_hora.desc()).all()
    
    return render_template('articulos/asignaciones.html', asignaciones=asignaciones)

@bp.route('/asignaciones/<int:persona_id>')
@login_required
def asignaciones_por_persona(persona_id):
    """Lista las asignaciones de una persona específica"""
    from app.database.models import Consumo, Persona, Item
    from app import db
    
    # Verificar que la persona existe
    persona = Persona.query.get(persona_id)
    if not persona:
        flash('Persona no encontrada', 'error')
        return redirect(url_for('articulos.listar_asignaciones'))
    
    # Obtener asignaciones de la persona
    asignaciones = db.session.query(Consumo, Persona, Item).join(
        Persona, Consumo.pe_id == Persona.id
    ).join(
        Item, Consumo.i_id == Item.id
    ).filter(Consumo.pe_id == persona_id).order_by(
        Consumo.c_fecha.desc(), Consumo.c_hora.desc()
    ).all()
    
    return render_template('articulos/asignaciones.html',
                         asignaciones=asignaciones,
                         persona_filtro=persona)

@bp.route('/asignaciones/<int:consumo_id>/cambiar-estado', methods=['POST'])
@login_required
def cambiar_estado_asignacion(consumo_id):
    """Cambia el estado de una asignación"""
    from app.database.models import Consumo
    from app import db
    
    try:
        consumo = Consumo.query.get(consumo_id)
        if not consumo:
            flash('Asignación no encontrada', 'error')
            return redirect(url_for('articulos.listar_asignaciones'))
        
        nuevo_estado = request.form['nuevo_estado']
        observaciones = request.form.get('observaciones', '')
        
        # Actualizar el estado
        consumo.c_estado = nuevo_estado
        
        # Agregar observaciones del cambio
        if observaciones:
            obs_anterior = consumo.c_observaciones or ''
            consumo.c_observaciones = f"{obs_anterior}\n[{nuevo_estado}] {observaciones}".strip()
        
        db.session.commit()
        
        flash(f'Estado cambiado a "{nuevo_estado}" exitosamente', 'success')
    except Exception as e:
        flash(f'Error al cambiar estado: {str(e)}', 'error')
    
    return redirect(request.referrer or url_for('articulos.listar_asignaciones'))

@bp.route('/<int:articulo_id>/salida', methods=['POST'])
@login_required
def registrar_salida(articulo_id):
    """Registra una salida de artículo con asignación a personal"""
    try:
        cantidad = int(request.form['cantidad'])
        valor_unitario = float(request.form['valor_unitario'])
        observaciones = request.form.get('observaciones', '')
        persona_id = request.form.get('persona_id')
        usuario_id = current_user.id
        
        # Validar que se haya seleccionado una persona
        if not persona_id:
            flash('Debe seleccionar una persona para asignar el artículo', 'error')
            return redirect(request.referrer or url_for('articulos.listar_articulos'))
        
        persona_id = int(persona_id)
        
        # Registrar la salida con asignación a personal
        articulo_service.registrar_salida_con_asignacion(
            articulo_id, cantidad, valor_unitario, usuario_id, persona_id, observaciones
        )
        
        flash('Artículo asignado exitosamente al personal', 'success')
    except ValueError as e:
        flash(str(e), 'error')
    except Exception as e:
        flash(f'Error al asignar artículo: {str(e)}', 'error')
    
    return redirect(request.referrer or url_for('articulos.listar_articulos'))