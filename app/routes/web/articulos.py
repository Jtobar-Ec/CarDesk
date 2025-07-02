from flask import Blueprint, render_template, request, redirect, url_for, flash, make_response
from flask_login import login_required, current_user
from app.services import ArticuloService
from app.services.proveedor_service import ProveedorService
from sqlalchemy import desc, asc
from app.database.models import Articulo, Item, Consumo, Persona
from app.database import db
import io
from openpyxl import Workbook
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch
from datetime import datetime
from app.utils.export_utils import (
    crear_cabecera_excel, crear_estilos_excel, crear_cabecera_pdf,
    crear_estilos_pdf, aplicar_estilo_tabla_pdf, ajustar_columnas_excel,
    crear_tabla_detallada_excel, crear_tabla_detallada_pdf,
    formatear_valor_moneda, formatear_fecha, truncar_texto
)

bp = Blueprint('articulos', __name__)
articulo_service = ArticuloService()
proveedor_service = ProveedorService()

@bp.route('/')
@login_required
def listar_articulos():
    """Lista todos los artículos con filtros, paginación y exportación"""
    # Parámetros de filtrado
    q = request.args.get('q', '').strip()
    estado_stock = request.args.get('estado_stock', '')
    orden = request.args.get('orden', 'reciente')
    per_page = int(request.args.get('per_page', 25))
    page = int(request.args.get('page', 1))
    export_format = request.args.get('export')
    
    # Query base
    query = db.session.query(Articulo, Item).join(Item, Articulo.i_id == Item.id)
    
    # Aplicar filtros
    if q:
        query = query.filter(
            db.or_(
                Item.i_nombre.ilike(f'%{q}%'),
                Item.i_codigo.ilike(f'%{q}%')
            )
        )
    
    if estado_stock:
        if estado_stock == 'critico':
            query = query.filter(Item.i_cantidad < Articulo.a_stockMin)
        elif estado_stock == 'bajo':
            query = query.filter(
                db.and_(
                    Item.i_cantidad >= Articulo.a_stockMin,
                    Item.i_cantidad <= (Articulo.a_stockMin * 1.2)
                )
            )
        elif estado_stock == 'normal':
            query = query.filter(Item.i_cantidad > (Articulo.a_stockMin * 1.2))
    
    # Aplicar ordenamiento
    if orden == 'nombre':
        query = query.order_by(asc(Item.i_nombre))
    elif orden == 'stock':
        query = query.order_by(desc(Item.i_cantidad))
    elif orden == 'valor':
        query = query.order_by(desc(Item.i_vTotal))
    else:  # reciente
        query = query.order_by(desc(Item.created_at))
    
    # Manejar exportaciones
    if export_format in ['excel', 'pdf']:
        articulos = query.all()
        if export_format == 'excel':
            return _exportar_excel(articulos)
        else:
            return _exportar_pdf(articulos)
    
    # Paginación
    pagination = query.paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    # Obtener proveedores para los modales de entrada
    proveedores = proveedor_service.obtener_todos()
    
    return render_template('articulos/list.html',
                         articulos=pagination.items,
                         pagination=pagination,
                         proveedores=proveedores)

def _exportar_excel(articulos):
    """Exporta artículos a Excel con formato detallado y profesional"""
    wb = Workbook()
    ws = wb.active
    ws.title = "Artículos Detallado"
    
    # Configurar orientación horizontal
    ws.page_setup.orientation = ws.ORIENTATION_LANDSCAPE
    
    # Crear cabecera institucional
    current_row = crear_cabecera_excel(ws, "Reporte Detallado de Artículos")
    
    # Preparar datos detallados con estadísticas
    headers = [
        'Código', 'Nombre del Artículo', 'Stock Actual', 'Valor Unitario', 'Valor Total',
        'Stock Mínimo', 'Stock Máximo', 'Estado de Stock', 'Cuenta Contable',
        'Fecha Creación', 'Diferencia vs Stock Min', 'Rotación Sugerida'
    ]
    
    data = []
    total_valor = 0
    articulos_criticos = 0
    articulos_bajos = 0
    
    for articulo, item in articulos:
        # Determinar estado detallado
        if item.i_cantidad < articulo.a_stockMin:
            estado = "CRÍTICO"
            articulos_criticos += 1
        elif item.i_cantidad <= (articulo.a_stockMin * 1.2):
            estado = "BAJO"
            articulos_bajos += 1
        else:
            estado = "NORMAL"
        
        # Calcular diferencia con stock mínimo
        diferencia = item.i_cantidad - articulo.a_stockMin
        
        # Sugerir rotación
        if diferencia < 0:
            rotacion = "URGENTE - Reabastecer"
        elif diferencia <= 5:
            rotacion = "Próximo a reabastecer"
        else:
            rotacion = "Stock suficiente"
        
        total_valor += float(item.i_vTotal)
        
        data.append([
            item.i_codigo,
            item.i_nombre,
            item.i_cantidad,
            formatear_valor_moneda(item.i_vUnitario),
            formatear_valor_moneda(item.i_vTotal),
            articulo.a_stockMin,
            articulo.a_stockMax,
            estado,
            articulo.a_c_contable or 'N/A',
            formatear_fecha(item.created_at),
            diferencia,
            rotacion
        ])
    
    # Crear tabla detallada
    current_row = crear_tabla_detallada_excel(ws, headers, data, current_row, "INVENTARIO DETALLADO DE ARTÍCULOS")
    
    # Agregar resumen estadístico completo
    current_row += 2
    ws[f'A{current_row}'] = "ANÁLISIS ESTADÍSTICO DEL INVENTARIO"
    ws[f'A{current_row}'].font = Font(name='Calibri', size=14, bold=True, color="2E5984")
    ws.merge_cells(f'A{current_row}:F{current_row}')
    current_row += 2
    
    resumen_headers = ['Métrica', 'Valor', 'Porcentaje', 'Observaciones']
    resumen_data = [
        ['Total de Artículos', len(articulos), '100%', 'Inventario completo'],
        ['Artículos en Estado Crítico', articulos_criticos, f"{(articulos_criticos/len(articulos)*100):.1f}%" if articulos else "0%", 'Requieren atención inmediata'],
        ['Artículos con Stock Bajo', articulos_bajos, f"{(articulos_bajos/len(articulos)*100):.1f}%" if articulos else "0%", 'Próximos a reabastecimiento'],
        ['Artículos con Stock Normal', len(articulos)-articulos_criticos-articulos_bajos, f"{((len(articulos)-articulos_criticos-articulos_bajos)/len(articulos)*100):.1f}%" if articulos else "0%", 'Stock adecuado'],
        ['Valor Total del Inventario', formatear_valor_moneda(total_valor), '100%', 'Valor total en stock'],
        ['Promedio Valor por Artículo', formatear_valor_moneda(total_valor/len(articulos)) if articulos else "$0.00", 'N/A', 'Valor promedio unitario']
    ]
    
    current_row = crear_tabla_detallada_excel(ws, resumen_headers, resumen_data, current_row)
    
    # Ajustar ancho de columnas
    ajustar_columnas_excel(ws)
    
    # Crear respuesta
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    
    response = make_response(output.read())
    response.headers['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    response.headers['Content-Disposition'] = f'attachment; filename=CNM_Articulos_Detallado_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
    
    return response

def _exportar_pdf(articulos):
    """Exporta artículos a PDF con formato detallado y profesional"""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4),
                          rightMargin=0.5*inch, leftMargin=0.5*inch,
                          topMargin=0.5*inch, bottomMargin=0.5*inch)
    
    elements = []
    
    # Crear cabecera institucional
    elements.extend(crear_cabecera_pdf("Reporte Detallado de Artículos"))
    
    # Calcular estadísticas
    total_valor = sum(float(item.i_vTotal) for _, item in articulos)
    articulos_criticos = sum(1 for articulo, item in articulos if item.i_cantidad < articulo.a_stockMin)
    articulos_bajos = sum(1 for articulo, item in articulos if articulo.a_stockMin <= item.i_cantidad <= (articulo.a_stockMin * 1.2))
    
    # Resumen estadístico
    resumen_headers = ['Métrica', 'Cantidad', 'Porcentaje', 'Valor']
    resumen_data = [
        ['Total Artículos', str(len(articulos)), '100%', formatear_valor_moneda(total_valor)],
        ['Estado Crítico', str(articulos_criticos), f"{(articulos_criticos/len(articulos)*100):.1f}%" if articulos else "0%", 'Requiere atención'],
        ['Stock Bajo', str(articulos_bajos), f"{(articulos_bajos/len(articulos)*100):.1f}%" if articulos else "0%", 'Próximo reabastecimiento'],
        ['Stock Normal', str(len(articulos)-articulos_criticos-articulos_bajos), f"{((len(articulos)-articulos_criticos-articulos_bajos)/len(articulos)*100):.1f}%" if articulos else "0%", 'Stock adecuado']
    ]
    
    elements.extend(crear_tabla_detallada_pdf(
        resumen_headers, resumen_data,
        "RESUMEN ESTADÍSTICO DEL INVENTARIO",
        [2*inch, 1*inch, 1*inch, 1.5*inch]
    ))
    
    # Datos detallados de la tabla
    data_headers = ['Código', 'Nombre', 'Stock', 'V.Unit', 'V.Total', 'Min/Max', 'Estado']
    data = []
    
    for articulo, item in articulos:
        # Determinar estado
        if item.i_cantidad < articulo.a_stockMin:
            estado = "CRÍTICO"
        elif item.i_cantidad <= (articulo.a_stockMin * 1.2):
            estado = "BAJO"
        else:
            estado = "NORMAL"
        
        data.append([
            item.i_codigo,
            truncar_texto(item.i_nombre, 20),
            str(item.i_cantidad),
            formatear_valor_moneda(item.i_vUnitario),
            formatear_valor_moneda(item.i_vTotal),
            f"{articulo.a_stockMin}/{articulo.a_stockMax}",
            estado
        ])
    
    # Crear tabla detallada de artículos
    elements.extend(crear_tabla_detallada_pdf(
        data_headers, data,
        "INVENTARIO DETALLADO DE ARTÍCULOS",
        [0.8*inch, 2*inch, 0.6*inch, 0.8*inch, 0.8*inch, 0.8*inch, 0.8*inch]
    ))
    
    # Construir PDF
    doc.build(elements)
    buffer.seek(0)
    
    response = make_response(buffer.read())
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename=CNM_Articulos_Detallado_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf'
    
    return response
    
    for articulo, item in articulos:
        # Determinar estado
        if item.i_cantidad < articulo.a_stockMin:
            estado = "Crítico"
        elif item.i_cantidad <= (articulo.a_stockMin * 1.2):
            estado = "Bajo"
        else:
            estado = "Normal"
        
        data.append([
            item.i_codigo,
            item.i_nombre[:25] + '...' if len(item.i_nombre) > 25 else item.i_nombre,
            str(item.i_cantidad),
            f"${float(item.i_vUnitario):.2f}",
            f"${float(item.i_vTotal):.2f}",
            f"{articulo.a_stockMin}/{articulo.a_stockMax}",
            estado,
            articulo.a_c_contable
        ])
    
    # Crear tabla
    table = Table(data, colWidths=[0.8*inch, 2.2*inch, 0.6*inch, 0.8*inch, 0.8*inch, 0.8*inch, 0.7*inch, 0.8*inch])
    
    # Aplicar estilo estandarizado
    aplicar_estilo_tabla_pdf(table)
    
    elements.append(table)
    
    # Construir PDF
    doc.build(elements)
    buffer.seek(0)
    
    response = make_response(buffer.read())
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename=CNM_Articulos_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf'
    
    return response

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
                    item.id, cantidad, valor_unitario, current_user.id,
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
    export_format = request.args.get('export')
    
    resultado = articulo_service.obtener_articulo_por_id(articulo_id)
    if not resultado:
        flash('Artículo no encontrado', 'error')
        return redirect(url_for('articulos.listar_articulos'))
    
    articulo = resultado
    item = articulo.item
    
    # Parámetros de filtrado para movimientos
    tipo_mov = request.args.get('tipo_mov', '')
    fecha_desde_mov = request.args.get('fecha_desde_mov', '')
    fecha_hasta_mov = request.args.get('fecha_hasta_mov', '')
    page_mov = int(request.args.get('page_mov', 1))
    per_page_mov = int(request.args.get('per_page_mov', 10))
    
    # Obtener TODOS los movimientos para cálculos (sin filtros)
    from app.database.models import MovimientoDetalle
    todos_movimientos = db.session.query(MovimientoDetalle).filter_by(
        i_id=item.id
    ).order_by(MovimientoDetalle.m_fecha.asc(), MovimientoDetalle.id.asc()).all()
    
    # Calcular valores totales con TODOS los movimientos
    stock_actual = 0
    saldo_calculado = 0
    valor_total_historico = 0
    valor_total_actual = 0
    
    for mov in todos_movimientos:
        mov.m_stock_anterior = stock_actual
        
        if mov.m_tipo == 'entrada':
            stock_actual += mov.m_cantidad
            saldo_calculado += mov.m_cantidad
            valor_total_historico += mov.m_valorTotal
            valor_total_actual += mov.m_valorTotal
        elif mov.m_tipo == 'salida':
            stock_actual -= mov.m_cantidad
            valor_total_actual -= mov.m_valorTotal
        
        mov.m_stock_actual = stock_actual
    
    # Query para movimientos con filtros y paginación
    query_mov = db.session.query(MovimientoDetalle).filter_by(i_id=item.id)
    
    if tipo_mov:
        query_mov = query_mov.filter(MovimientoDetalle.m_tipo == tipo_mov)
    
    if fecha_desde_mov:
        try:
            from datetime import datetime
            fecha_desde_obj = datetime.strptime(fecha_desde_mov, '%Y-%m-%d').date()
            query_mov = query_mov.filter(MovimientoDetalle.m_fecha >= fecha_desde_obj)
        except ValueError:
            pass
    
    if fecha_hasta_mov:
        try:
            from datetime import datetime
            fecha_hasta_obj = datetime.strptime(fecha_hasta_mov, '%Y-%m-%d').date()
            query_mov = query_mov.filter(MovimientoDetalle.m_fecha <= fecha_hasta_obj)
        except ValueError:
            pass
    
    # Paginación de movimientos
    pagination_mov = query_mov.order_by(MovimientoDetalle.m_fecha.desc()).paginate(
        page=page_mov, per_page=per_page_mov, error_out=False
    )
    
    # Aplicar cálculos de stock a movimientos paginados
    movimientos_dict = {mov.id: mov for mov in todos_movimientos}
    for mov in pagination_mov.items:
        if mov.id in movimientos_dict:
            mov.m_stock_anterior = movimientos_dict[mov.id].m_stock_anterior
            mov.m_stock_actual = movimientos_dict[mov.id].m_stock_actual
    
    # Obtener auditoría de cambios (movimientos que registran cambios)
    auditoria = db.session.query(MovimientoDetalle).filter_by(
        i_id=item.id
    ).filter(
        MovimientoDetalle.m_tipo.in_(['ajuste_precio', 'entrada', 'salida'])
    ).order_by(MovimientoDetalle.m_fecha.desc()).limit(20).all()
    
    # Manejar exportaciones
    if export_format in ['excel', 'pdf']:
        if export_format == 'excel':
            return _exportar_articulos_excel(articulo, item, todos_movimientos, saldo_calculado)
        else:
            return _exportar_articulos_pdf(articulo, item, todos_movimientos, saldo_calculado)
    
    # Obtener todos los proveedores para el modal
    proveedores = proveedor_service.obtener_todos()
    
    return render_template('articulos/detail.html',
                         articulo=articulo, item=item, movimientos=pagination_mov.items,
                         pagination_mov=pagination_mov, saldo_calculado=saldo_calculado,
                         auditoria=auditoria, proveedores=proveedores,
                         valor_total_historico=valor_total_historico,
                         valor_total_actual=valor_total_actual)

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
        
        # Obtener el item_id correcto
        resultado = articulo_service.obtener_por_id(articulo_id)
        if not resultado:
            flash('Artículo no encontrado', 'error')
            return redirect(request.referrer or url_for('articulos.listar_articulos'))
        
        articulo, item = resultado
        
        from datetime import datetime
        articulo_service.registrar_entrada(
            item.id, cantidad, valor_unitario, usuario_id,
            proveedor_id=proveedor_id, observaciones=observaciones,
            fecha_hora=datetime.now()
        )
        
        flash('Entrada registrada exitosamente', 'success')
    except Exception as e:
        flash(f'Error al registrar entrada: {str(e)}', 'error')
    
    return redirect(request.referrer or url_for('articulos.listar_articulos'))

@bp.route('/asignaciones')
@login_required
def listar_asignaciones():
    """Lista todas las asignaciones de artículos a personal con filtros y paginación"""
    from app.database.models import Consumo, Persona, Item
    from app import db
    
    # Obtener filtros y paginación
    estado = request.args.get('estado', '').strip()
    articulo = request.args.get('articulo', '').strip()
    persona = request.args.get('persona', '').strip()
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    # Query base
    query = db.session.query(Consumo, Persona, Item).join(
        Persona, Consumo.pe_id == Persona.id
    ).join(
        Item, Consumo.i_id == Item.id
    )
    
    # Aplicar filtros
    if estado:
        query = query.filter(Consumo.c_estado == estado)
    
    if articulo and articulo.lower() != 'none':
        query = query.filter(
            db.or_(
                Item.i_nombre.ilike(f'%{articulo}%'),
                Item.i_codigo.ilike(f'%{articulo}%')
            )
        )
    
    if persona and persona.lower() != 'none':
        query = query.filter(
            db.or_(
                Persona.pe_nombre.ilike(f'%{persona}%'),
                Persona.pe_apellido.ilike(f'%{persona}%')
            )
        )
    
    # Ordenar por fecha descendente (más recientes primero) y paginar
    pagination = query.order_by(Consumo.c_fecha.desc(), Consumo.c_hora.desc())\
                     .paginate(page=page, per_page=per_page, error_out=False)
    
    return render_template('articulos/asignaciones.html',
                         asignaciones=pagination.items,
                         pagination=pagination)

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
    
    # Paginación
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    # Obtener asignaciones de la persona con paginación
    pagination = db.session.query(Consumo, Persona, Item).join(
        Persona, Consumo.pe_id == Persona.id
    ).join(
        Item, Consumo.i_id == Item.id
    ).filter(Consumo.pe_id == persona_id).order_by(
        Consumo.c_fecha.desc(), Consumo.c_hora.desc()
    ).paginate(page=page, per_page=per_page, error_out=False)
    
    return render_template('articulos/asignaciones.html',
                         asignaciones=pagination.items,
                         pagination=pagination,
                         persona_filtro=persona)

@bp.route('/asignaciones/<int:consumo_id>/cambiar-estado', methods=['POST'])
@login_required
def cambiar_estado_asignacion(consumo_id):
    """Cambia el estado de una asignación con lógica de retorno de stock"""
    from app.database.models import Consumo, Item
    from datetime import datetime
    
    try:
        consumo = Consumo.query.get(consumo_id)
        if not consumo:
            flash('Asignación no encontrada', 'error')
            return redirect(url_for('articulos.listar_asignaciones'))
        
        # Verificar si puede editarse (48 horas)
        if not consumo.puede_editar_por_tiempo:
            flash('No se puede modificar esta asignación. Han pasado más de 48 horas desde su creación.', 'error')
            return redirect(request.referrer or url_for('articulos.listar_asignaciones'))
        
        nuevo_estado = request.form['nuevo_estado']
        observaciones = request.form.get('observaciones', '')
        estado_anterior = consumo.c_estado
        
        # Solo "Devuelto" retorna stock al inventario
        if nuevo_estado == 'Devuelto' and estado_anterior != 'Devuelto':
            item = Item.query.get(consumo.i_id)
            if item:
                # Solo retornar la cantidad física al stock
                item.i_cantidad += consumo.c_cantidad
                consumo.c_fecha_devolucion = datetime.utcnow()
        
        # Si se cambia de "Devuelto" a cualquier otro estado, descontar stock
        elif estado_anterior == 'Devuelto' and nuevo_estado != 'Devuelto':
            item = Item.query.get(consumo.i_id)
            if item:
                if item.i_cantidad >= consumo.c_cantidad:
                    item.i_cantidad -= consumo.c_cantidad
                    consumo.c_fecha_devolucion = None
                else:
                    flash(f'No hay suficiente stock disponible. Stock actual: {item.i_cantidad}', 'error')
                    return redirect(request.referrer or url_for('articulos.listar_asignaciones'))
        
        # Actualizar el estado
        consumo.c_estado = nuevo_estado
        
        # Agregar observaciones del cambio
        if observaciones:
            obs_anterior = consumo.c_observaciones or ''
            timestamp = datetime.now().strftime('%d/%m/%Y %H:%M')
            consumo.c_observaciones = f"{obs_anterior}\n[{timestamp} - {nuevo_estado}] {observaciones}".strip()
        
        db.session.commit()
        
        flash(f'Estado cambiado a "{nuevo_estado}" exitosamente', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error al cambiar estado: {str(e)}', 'error')
    
    return redirect(request.referrer or url_for('articulos.listar_asignaciones'))

@bp.route('/movimientos')
@login_required
def listar_movimientos():
    """Lista todos los movimientos de inventario con filtros y paginación"""
    from app.database.models import MovimientoDetalle, Item, Usuario, Entrada, Proveedor
    from datetime import datetime
    
    # Parámetros de filtrado
    buscar = request.args.get('buscar', '').strip()
    tipo = request.args.get('tipo', '')
    fecha_desde = request.args.get('fecha_desde', '')
    fecha_hasta = request.args.get('fecha_hasta', '')
    per_page = 20
    page = int(request.args.get('page', 1))
    export_format = request.args.get('export')
    
    # Query base con joins
    query = db.session.query(MovimientoDetalle, Item, Usuario).join(
        Item, MovimientoDetalle.i_id == Item.id
    ).join(
        Usuario, MovimientoDetalle.u_id == Usuario.id
    )
    
    # Aplicar filtros
    if buscar:
        query = query.filter(
            db.or_(
                Item.i_nombre.ilike(f'%{buscar}%'),
                Item.i_codigo.ilike(f'%{buscar}%'),
                MovimientoDetalle.m_observaciones.ilike(f'%{buscar}%')
            )
        )
    
    if tipo:
        query = query.filter(MovimientoDetalle.m_tipo == tipo)
    
    if fecha_desde:
        try:
            fecha_desde_obj = datetime.strptime(fecha_desde, '%Y-%m-%d').date()
            query = query.filter(MovimientoDetalle.m_fecha >= fecha_desde_obj)
        except ValueError:
            pass
    
    if fecha_hasta:
        try:
            fecha_hasta_obj = datetime.strptime(fecha_hasta, '%Y-%m-%d').date()
            query = query.filter(MovimientoDetalle.m_fecha <= fecha_hasta_obj)
        except ValueError:
            pass
    
    # Ordenar por fecha descendente
    query = query.order_by(desc(MovimientoDetalle.m_fecha), desc(MovimientoDetalle.id))
    
    # Manejar exportaciones
    if export_format in ['excel', 'pdf']:
        movimientos = query.all()
        if export_format == 'excel':
            return _exportar_movimientos_excel(movimientos)
        else:
            return _exportar_movimientos_pdf(movimientos)
    
    # Paginación
    pagination = query.paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return render_template('articulos/movimientos.html',
                         movimientos=pagination.items,
                         pagination=pagination)

def _exportar_movimientos_excel(movimientos):
    """Exporta movimientos a Excel con cabecera institucional"""
    wb = Workbook()
    ws = wb.active
    ws.title = "Movimientos"
    
    # Configurar orientación horizontal
    ws.page_setup.orientation = ws.ORIENTATION_LANDSCAPE
    
    # Crear cabecera institucional
    current_row = crear_cabecera_excel(ws, "Reporte de Movimientos de Inventario")
    
    # Obtener estilos
    estilos = crear_estilos_excel()
    
    # Encabezados de datos
    headers = ['Fecha', 'Artículo', 'Código', 'Tipo', 'Cantidad', 'Valor Unit.',
               'Valor Total', 'Usuario', 'Proveedor', 'Observaciones']
    
    # Escribir encabezados
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=current_row, column=col, value=header)
        cell.font = estilos['header_font']
        cell.fill = estilos['header_fill']
        cell.alignment = estilos['header_alignment']
        cell.border = estilos['header_border']
    current_row += 1
    
    # Escribir datos
    for movimiento, item, usuario in movimientos:
        # Obtener proveedor si existe
        proveedor_nombre = ""
        if movimiento.e_id and movimiento.entrada and movimiento.entrada.proveedor:
            proveedor_nombre = movimiento.entrada.proveedor.p_razonsocial
        
        ws.cell(row=current_row, column=1, value=movimiento.m_fecha.strftime('%Y-%m-%d'))
        ws.cell(row=current_row, column=2, value=item.i_nombre)
        ws.cell(row=current_row, column=3, value=item.i_codigo)
        ws.cell(row=current_row, column=4, value=movimiento.m_tipo.title())
        ws.cell(row=current_row, column=5, value=movimiento.m_cantidad)
        ws.cell(row=current_row, column=6, value=float(movimiento.m_valorUnitario))
        ws.cell(row=current_row, column=7, value=float(movimiento.m_valorTotal))
        ws.cell(row=current_row, column=8, value=usuario.u_username)
        ws.cell(row=current_row, column=9, value=proveedor_nombre)
        ws.cell(row=current_row, column=10, value=movimiento.m_observaciones or '')
        
        # Aplicar estilos a los datos
        for col in range(1, 11):
            cell = ws.cell(row=current_row, column=col)
            cell.font = estilos['data_font']
            cell.border = estilos['data_border']
        
        current_row += 1
    
    # Ajustar ancho de columnas
    ajustar_columnas_excel(ws)
    
    # Crear respuesta
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    
    response = make_response(output.read())
    response.headers['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    response.headers['Content-Disposition'] = f'attachment; filename=CNM_Movimientos_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
    
    return response

def _exportar_movimientos_pdf(movimientos):
    """Exporta movimientos a PDF con cabecera institucional"""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4),
                          rightMargin=0.5*inch, leftMargin=0.5*inch,
                          topMargin=0.5*inch, bottomMargin=0.5*inch)
    
    elements = []
    
    # Crear cabecera institucional
    elements.extend(crear_cabecera_pdf("Reporte de Movimientos de Inventario"))
    
    # Obtener estilos
    styles = crear_estilos_pdf()
    
    # Título de la sección de datos
    elements.append(Paragraph("LISTADO DE MOVIMIENTOS", styles['TituloSeccion']))
    elements.append(Paragraph(f"Total de registros: {len(movimientos)}", styles['Normal']))
    elements.append(Spacer(1, 12))
    
    # Datos de la tabla
    data = [['Fecha', 'Artículo', 'Tipo', 'Cantidad', 'Valor Unit.', 'Valor Total', 'Usuario', 'Observaciones']]
    
    for movimiento, item, usuario in movimientos:
        data.append([
            movimiento.m_fecha.strftime('%d/%m/%Y'),
            item.i_nombre[:20] + '...' if len(item.i_nombre) > 20 else item.i_nombre,
            movimiento.m_tipo.title(),
            str(movimiento.m_cantidad),
            f"${float(movimiento.m_valorUnitario):.2f}",
            f"${float(movimiento.m_valorTotal):.2f}",
            usuario.u_username,
            (movimiento.m_observaciones or '')[:25] + '...' if movimiento.m_observaciones and len(movimiento.m_observaciones) > 25 else (movimiento.m_observaciones or '')
        ])
    
    # Crear tabla
    table = Table(data, colWidths=[0.8*inch, 2.0*inch, 0.7*inch, 0.6*inch, 0.8*inch, 0.8*inch, 0.8*inch, 1.8*inch])
    
    # Aplicar estilo estandarizado
    aplicar_estilo_tabla_pdf(table)
    
    elements.append(table)
    
    # Construir PDF
    doc.build(elements)
    buffer.seek(0)
    
    response = make_response(buffer.read())
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename=CNM_Movimientos_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf'
    
    return response

def _exportar_articulos_excel(articulo, item, movimientos, saldo_calculado):
    """Exporta detalle de artículo a Excel con cabecera institucional"""
    wb = Workbook()
    ws = wb.active
    ws.title = f"Detalle {item.i_codigo}"
    
    # Configurar orientación horizontal
    ws.page_setup.orientation = ws.ORIENTATION_LANDSCAPE
    
    # Crear cabecera institucional
    current_row = crear_cabecera_excel(ws, f"Detalle de Artículo - {item.i_codigo}")
    
    # Obtener estilos
    estilos = crear_estilos_excel()
    
    # Información del artículo
    info_headers = ['Campo', 'Valor']
    for col, header in enumerate(info_headers, 1):
        cell = ws.cell(row=current_row, column=col, value=header)
        cell.font = estilos['header_font']
        cell.fill = estilos['header_fill']
        cell.alignment = estilos['header_alignment']
        cell.border = estilos['header_border']
    current_row += 1
    
    # Datos del artículo
    info_data = [
        ['Código', item.i_codigo],
        ['Nombre', item.i_nombre],
        ['Stock Actual', item.i_cantidad],
        ['Saldo Calculado', saldo_calculado],
        ['Valor Unitario', f"${float(item.i_vUnitario):.2f}"],
        ['Stock Mínimo', articulo.a_stockMin],
        ['Stock Máximo', articulo.a_stockMax],
        ['Cuenta Contable', articulo.a_c_contable]
    ]
    
    for campo, valor in info_data:
        ws.cell(row=current_row, column=1, value=campo).font = estilos['data_font']
        ws.cell(row=current_row, column=2, value=valor).font = estilos['data_font']
        current_row += 1
    
    current_row += 2  # Espacio antes de movimientos
    
    # Título de movimientos
    ws.cell(row=current_row, column=1, value="HISTORIAL DE MOVIMIENTOS").font = estilos['header_font']
    current_row += 2
    
    # Encabezados de movimientos
    row_start = current_row
    headers = ['Fecha', 'Tipo', 'Cantidad', 'Valor Unit.', 'Valor Total', 'Usuario', 'Observaciones']
    
    # Escribir encabezados de movimientos
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=row_start, column=col, value=header)
        cell.font = estilos['header_font']
        cell.fill = estilos['header_fill']
        cell.alignment = estilos['header_alignment']
        cell.border = estilos['header_border']
    row_start += 1
    
    # Escribir datos de movimientos
    for mov in movimientos:
        ws.cell(row=row_start, column=1, value=mov.m_fecha.strftime('%Y-%m-%d'))
        ws.cell(row=row_start, column=2, value=mov.m_tipo.title())
        ws.cell(row=row_start, column=3, value=mov.m_cantidad)
        ws.cell(row=row_start, column=4, value=float(mov.m_valorUnitario))
        ws.cell(row=row_start, column=5, value=float(mov.m_valorTotal))
        ws.cell(row=row_start, column=6, value=mov.u_id)
        ws.cell(row=row_start, column=7, value=mov.m_observaciones or '')
        
        # Aplicar estilos a los datos
        for col in range(1, 8):
            cell = ws.cell(row=row_start, column=col)
            cell.font = estilos['data_font']
            cell.border = estilos['data_border']
        
        row_start += 1
    
    # Ajustar ancho de columnas
    ajustar_columnas_excel(ws)
    
    # Crear respuesta
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    
    response = make_response(output.read())
    response.headers['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    response.headers['Content-Disposition'] = f'attachment; filename=CNM_Detalle_{item.i_codigo}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
    
    return response

def _exportar_articulos_pdf(articulo, item, movimientos, saldo_calculado):
    """Exporta detalle de artículo a PDF con cabecera institucional"""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4),
                          rightMargin=0.5*inch, leftMargin=0.5*inch,
                          topMargin=0.5*inch, bottomMargin=0.5*inch)
    
    elements = []
    
    # Crear cabecera institucional
    elements.extend(crear_cabecera_pdf(f"Detalle de Artículo - {item.i_codigo}"))
    
    # Obtener estilos
    styles = crear_estilos_pdf()
    
    # Título de la sección de información
    elements.append(Paragraph("INFORMACIÓN DEL ARTÍCULO", styles['TituloSeccion']))
    elements.append(Spacer(1, 12))
    
    # Información del artículo
    info_data = [
        ['Código:', item.i_codigo, 'Stock Actual:', str(item.i_cantidad)],
        ['Nombre:', item.i_nombre, 'Saldo Calculado:', str(saldo_calculado)],
        ['Valor Unitario:', f"${float(item.i_vUnitario):.2f}", 'Valor Total:', f"${float(item.i_vTotal):.2f}"],
        ['Stock Mín/Máx:', f"{articulo.a_stockMin}/{articulo.a_stockMax}", 'Cuenta Contable:', articulo.a_c_contable]
    ]
    
    info_table = Table(info_data, colWidths=[1.2*inch, 2.5*inch, 1.2*inch, 1.5*inch])
    info_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))
    
    elements.append(info_table)
    elements.append(Spacer(1, 20))
    
    # Título de movimientos
    elements.append(Paragraph("HISTORIAL DE MOVIMIENTOS", styles['TituloSeccion']))
    elements.append(Paragraph(f"Mostrando los últimos 20 movimientos", styles['Normal']))
    elements.append(Spacer(1, 12))
    
    # Tabla de movimientos
    mov_data = [['Fecha', 'Tipo', 'Cantidad', 'Valor Unit.', 'Valor Total', 'Observaciones']]
    
    for mov in movimientos[:20]:  # Limitar a 20 movimientos más recientes
        mov_data.append([
            mov.m_fecha.strftime('%d/%m/%Y'),
            mov.m_tipo.title(),
            str(mov.m_cantidad),
            f"${float(mov.m_valorUnitario):.2f}",
            f"${float(mov.m_valorTotal):.2f}",
            (mov.m_observaciones or '')[:30] + '...' if mov.m_observaciones and len(mov.m_observaciones) > 30 else (mov.m_observaciones or '')
        ])
    
    mov_table = Table(mov_data, colWidths=[0.8*inch, 0.8*inch, 0.8*inch, 0.8*inch, 0.8*inch, 2.5*inch])
    
    # Aplicar estilo estandarizado
    aplicar_estilo_tabla_pdf(mov_table)
    
    elements.append(mov_table)
    
    # Construir PDF
    doc.build(elements)
    buffer.seek(0)
    
    response = make_response(buffer.read())
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename=CNM_Detalle_{item.i_codigo}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf'
    
    return response

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

@bp.route('/exportar_asignaciones')
@login_required
def exportar_asignaciones():
    """Exportar historial de asignaciones a Excel o PDF"""
    export_format = request.args.get('export_format')
    
    # Obtener los filtros de la URL
    estado = request.args.get('estado', '').strip()
    articulo = request.args.get('articulo', '').strip()
    persona = request.args.get('persona', '').strip()

    # Construir la consulta base
    query = db.session.query(Consumo, Persona, Item).join(Persona, Consumo.pe_id == Persona.id).join(Item, Consumo.i_id == Item.id)

    # Aplicar filtros
    if estado:
        query = query.filter(Consumo.c_estado == estado)
    
    if articulo and articulo.lower() != "none":
        query = query.filter(
            db.or_(
                Item.i_nombre.ilike(f'%{articulo}%'),
                Item.i_codigo.ilike(f'%{articulo}%')
            )
        )
    
    if persona and persona.lower() != "none":
        query = query.filter(
            db.or_(
                Persona.pe_nombre.ilike(f'%{persona}%'),
                Persona.pe_apellido.ilike(f'%{persona}%')
            )
        )

    # Obtener los resultados con los filtros aplicados
    asignaciones = query.order_by(Consumo.c_fecha.desc(), Consumo.c_hora.desc()).all()

    # Manejo de exportación a Excel o PDF
    if export_format == 'excel':
        return _exportar_asignaciones_excel(asignaciones)
    elif export_format == 'pdf':
        return _exportar_asignaciones_pdf(asignaciones)
    else:
        flash("Formato de exportación no soportado.", "error")
        return redirect(url_for('articulos.listar_asignaciones'))


def _exportar_asignaciones_excel(asignaciones):
    """Exporta el historial de asignaciones a Excel con cabecera institucional"""
    wb = Workbook()
    ws = wb.active
    ws.title = "Asignaciones"
    
    # Configurar orientación horizontal
    ws.page_setup.orientation = ws.ORIENTATION_LANDSCAPE
    
    # Crear cabecera institucional
    current_row = crear_cabecera_excel(ws, "Reporte de Asignaciones de Artículos")
    
    # Obtener estilos
    estilos = crear_estilos_excel()
    
    # Encabezados de datos
    headers = ['Fecha', 'Artículo', 'Personal', 'Cantidad', 'Valor Unitario', 'Valor Total', 'Estado', 'Observaciones']
    
    # Escribir encabezados
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=current_row, column=col, value=header)
        cell.font = estilos['header_font']
        cell.fill = estilos['header_fill']
        cell.alignment = estilos['header_alignment']
        cell.border = estilos['header_border']
    current_row += 1
    
    # Escribir datos
    for consumo, persona, item in asignaciones:
        ws.cell(row=current_row, column=1, value=consumo.c_fecha.strftime('%Y-%m-%d'))
        ws.cell(row=current_row, column=2, value=item.i_nombre)
        ws.cell(row=current_row, column=3, value=f"{persona.pe_nombre} {persona.pe_apellido}")
        ws.cell(row=current_row, column=4, value=consumo.c_cantidad)
        ws.cell(row=current_row, column=5, value=float(consumo.c_valorUnitario))
        ws.cell(row=current_row, column=6, value=float(consumo.c_valorTotal))
        ws.cell(row=current_row, column=7, value=consumo.c_estado)
        ws.cell(row=current_row, column=8, value=consumo.c_observaciones or '')
        
        # Aplicar estilos a los datos
        for col in range(1, 9):
            cell = ws.cell(row=current_row, column=col)
            cell.font = estilos['data_font']
            cell.border = estilos['data_border']
        
        current_row += 1
    
    # Ajustar ancho de columnas
    ajustar_columnas_excel(ws)
    
    # Crear respuesta
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    
    response = make_response(output.read())
    response.headers['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    response.headers['Content-Disposition'] = f'attachment; filename=CNM_Asignaciones_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
    
    return response


def _exportar_asignaciones_pdf(asignaciones):
    """Exporta el historial de asignaciones a PDF con cabecera institucional"""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4),
                          rightMargin=0.5*inch, leftMargin=0.5*inch,
                          topMargin=0.5*inch, bottomMargin=0.5*inch)

    elements = []
    
    # Crear cabecera institucional
    elements.extend(crear_cabecera_pdf("Reporte de Asignaciones de Artículos"))
    
    # Obtener estilos
    styles = crear_estilos_pdf()
    
    # Título de la sección de datos
    elements.append(Paragraph("LISTADO DE ASIGNACIONES", styles['TituloSeccion']))
    elements.append(Paragraph(f"Total de registros: {len(asignaciones)}", styles['Normal']))
    elements.append(Spacer(1, 12))

    # Datos de la tabla
    data = [['Fecha', 'Artículo', 'Personal', 'Cantidad', 'Valor Unit.', 'Valor Total', 'Estado', 'Observaciones']]
    
    for consumo, persona, item in asignaciones:
        data.append([
            consumo.c_fecha.strftime('%d/%m/%Y'),
            item.i_nombre[:20] + '...' if len(item.i_nombre) > 20 else item.i_nombre,
            f"{persona.pe_nombre} {persona.pe_apellido}"[:25] + '...' if len(f"{persona.pe_nombre} {persona.pe_apellido}") > 25 else f"{persona.pe_nombre} {persona.pe_apellido}",
            str(consumo.c_cantidad),
            f"${float(consumo.c_valorUnitario):.2f}",
            f"${float(consumo.c_valorTotal):.2f}",
            consumo.c_estado,
            (consumo.c_observaciones or '')[:20] + '...' if consumo.c_observaciones and len(consumo.c_observaciones) > 20 else (consumo.c_observaciones or 'Ninguna')
        ])

    # Crear tabla
    table = Table(data, colWidths=[0.8*inch, 1.8*inch, 1.5*inch, 0.6*inch, 0.8*inch, 0.8*inch, 0.8*inch, 1.4*inch])
    
    # Aplicar estilo estandarizado
    aplicar_estilo_tabla_pdf(table)
    
    elements.append(table)

    # Construir PDF
    doc.build(elements)
    buffer.seek(0)
    
    response = make_response(buffer.read())
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename=CNM_Asignaciones_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf'
    
    return response

