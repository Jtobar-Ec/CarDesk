from flask import Blueprint, render_template, request, redirect, url_for, flash, make_response
from flask_login import login_required, current_user
from app.services import ArticuloService
from app.services.proveedor_service import ProveedorService
from sqlalchemy import desc, asc
from app.database.models import Articulo, Item, Consumo, Persona
from app.database import db
import io
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch
from datetime import datetime

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
    
    return render_template('articulos/list.html',
                         articulos=pagination.items,
                         pagination=pagination)

def _exportar_excel(articulos):
    """Exporta artículos a Excel en orientación horizontal"""
    wb = Workbook()
    ws = wb.active
    ws.title = "Artículos"
    
    # Configurar orientación horizontal
    ws.page_setup.orientation = ws.ORIENTATION_LANDSCAPE
    
    # Encabezados
    headers = ['Código', 'Nombre', 'Stock Actual', 'Valor Unitario', 'Valor Total',
               'Stock Mínimo', 'Stock Máximo', 'Estado', 'Cuenta Contable', 'Fecha Creación']
    
    # Estilo para encabezados
    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
    header_alignment = Alignment(horizontal="center", vertical="center")
    
    # Escribir encabezados
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_alignment
    
    # Escribir datos
    for row, (articulo, item) in enumerate(articulos, 2):
        # Determinar estado
        if item.i_cantidad < articulo.a_stockMin:
            estado = "Crítico"
        elif item.i_cantidad <= (articulo.a_stockMin * 1.2):
            estado = "Bajo"
        else:
            estado = "Normal"
        
        ws.cell(row=row, column=1, value=item.i_codigo)
        ws.cell(row=row, column=2, value=item.i_nombre)
        ws.cell(row=row, column=3, value=item.i_cantidad)
        ws.cell(row=row, column=4, value=float(item.i_vUnitario))
        ws.cell(row=row, column=5, value=float(item.i_vTotal))
        ws.cell(row=row, column=6, value=articulo.a_stockMin)
        ws.cell(row=row, column=7, value=articulo.a_stockMax)
        ws.cell(row=row, column=8, value=estado)
        ws.cell(row=row, column=9, value=articulo.a_c_contable)
        ws.cell(row=row, column=10, value=item.created_at.strftime('%Y-%m-%d'))
    
    # Ajustar ancho de columnas
    for column in ws.columns:
        max_length = 0
        column_letter = column[0].column_letter
        for cell in column:
            try:
                if len(str(cell.value)) > max_length:
                    max_length = len(str(cell.value))
            except Exception:
                pass
        adjusted_width = min(max_length + 2, 50)
        ws.column_dimensions[column_letter].width = adjusted_width
    
    # Crear respuesta
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    
    response = make_response(output.read())
    response.headers['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    response.headers['Content-Disposition'] = f'attachment; filename=articulos_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
    
    return response

def _exportar_pdf(articulos):
    """Exporta artículos a PDF en orientación horizontal"""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4),
                          rightMargin=0.5*inch, leftMargin=0.5*inch,
                          topMargin=0.5*inch, bottomMargin=0.5*inch)
    
    elements = []
    styles = getSampleStyleSheet()
    
    # Título
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        spaceAfter=30,
        alignment=1  # Centrado
    )
    
    title = Paragraph("REPORTE DE ARTÍCULOS", title_style)
    elements.append(title)
    elements.append(Spacer(1, 12))
    
    # Información del reporte
    info_style = ParagraphStyle(
        'InfoStyle',
        parent=styles['Normal'],
        fontSize=10,
        spaceAfter=20
    )
    
    fecha_reporte = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
    info = Paragraph(f"<b>Fecha del reporte:</b> {fecha_reporte}<br/><b>Total de artículos:</b> {len(articulos)}", info_style)
    elements.append(info)
    elements.append(Spacer(1, 12))
    
    # Datos de la tabla
    data = [['Código', 'Nombre', 'Stock', 'Valor Unit.', 'Valor Total', 'Stock Min/Max', 'Estado', 'Cuenta']]
    
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
    
    # Estilo de la tabla
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    
    elements.append(table)
    
    # Construir PDF
    doc.build(elements)
    buffer.seek(0)
    
    response = make_response(buffer.read())
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename=articulos_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf'
    
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
    
    # Obtener movimientos del historial
    from app.database.models import MovimientoDetalle
    movimientos = db.session.query(MovimientoDetalle).filter_by(
        i_id=item.id
    ).order_by(MovimientoDetalle.m_fecha.asc(), MovimientoDetalle.id.asc()).all()
    
    # Calcular stock anterior y actual para cada movimiento
    stock_actual = 0
    for i, mov in enumerate(movimientos):
        # Stock anterior es el stock antes de este movimiento
        mov.m_stock_anterior = stock_actual
        
        # Aplicar el movimiento al stock
        if mov.m_tipo == 'entrada':
            stock_actual += mov.m_cantidad
        elif mov.m_tipo == 'salida':
            stock_actual -= mov.m_cantidad
        
        # Stock actual es el stock después de este movimiento
        mov.m_stock_actual = stock_actual
    
    # Calcular saldo final
    saldo_calculado = stock_actual
    
    # Invertir orden para mostrar más recientes primero
    movimientos.reverse()
    
    # Obtener auditoría de cambios (movimientos que registran cambios)
    auditoria = db.session.query(MovimientoDetalle).filter_by(
        i_id=item.id
    ).filter(
        MovimientoDetalle.m_tipo.in_(['ajuste_precio', 'entrada', 'salida'])
    ).order_by(MovimientoDetalle.m_fecha.desc()).limit(20).all()
    
    # Manejar exportaciones
    if export_format in ['excel', 'pdf']:
        if export_format == 'excel':
            return _exportar_articulos_excel(articulo, item, movimientos, saldo_calculado)
        else:
            return _exportar_articulos_pdf(articulo, item, movimientos, saldo_calculado)
    
    # Obtener todos los proveedores para el modal
    proveedores = proveedor_service.obtener_todos()
    
    return render_template('articulos/detail.html',
                         articulo=articulo, item=item, movimientos=movimientos,
                         saldo_calculado=saldo_calculado, auditoria=auditoria,
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
        
        # Obtener el item_id correcto
        resultado = articulo_service.obtener_por_id(articulo_id)
        if not resultado:
            flash('Artículo no encontrado', 'error')
            return redirect(request.referrer or url_for('articulos.listar_articulos'))
        
        articulo, item = resultado
        
        articulo_service.registrar_entrada(
            item.id, cantidad, valor_unitario, usuario_id,
            proveedor_id=proveedor_id, observaciones=observaciones
        )
        
        flash('Entrada registrada exitosamente', 'success')
    except Exception as e:
        flash(f'Error al registrar entrada: {str(e)}', 'error')
    
    return redirect(request.referrer or url_for('articulos.listar_articulos'))

@bp.route('/asignaciones')
@login_required
def listar_asignaciones():
    """Lista todas las asignaciones de artículos a personal con filtros"""
    from app.database.models import Consumo, Persona, Item
    from app import db
    
    # Obtener filtros
    estado = request.args.get('estado', '').strip()
    articulo = request.args.get('articulo', '').strip()
    persona = request.args.get('persona', '').strip()
    
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
    
    # Ordenar resultados
    asignaciones = query.order_by(Consumo.c_fecha.desc(), Consumo.c_hora.desc()).all()
    
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
        
        # Si se marca como "Devuelto", retornar stock
        if nuevo_estado == 'Devuelto' and estado_anterior != 'Devuelto':
            item = Item.query.get(consumo.i_id)
            if item:
                # Retornar la cantidad al stock
                item.i_cantidad += consumo.c_cantidad
                item.i_vTotal = item.i_cantidad * item.i_vUnitario
                
                # Registrar movimiento de entrada por devolución
                articulo_service.registrar_movimiento_devolucion(
                    item.id,
                    consumo.c_cantidad,
                    consumo.c_valorUnitario,
                    current_user.id,
                    f"Devolución de asignación #{consumo.id} - {consumo.persona.pe_nombre}"
                )
                
                consumo.c_fecha_devolucion = datetime.utcnow()
        
        # Si se cambia de "Devuelto" a otro estado, descontar stock nuevamente
        elif estado_anterior == 'Devuelto' and nuevo_estado != 'Devuelto':
            item = Item.query.get(consumo.i_id)
            if item:
                if item.i_cantidad >= consumo.c_cantidad:
                    # Descontar la cantidad del stock
                    item.i_cantidad -= consumo.c_cantidad
                    item.i_vTotal = item.i_cantidad * item.i_vUnitario
                    
                    # Registrar movimiento de salida por reasignación
                    articulo_service.registrar_movimiento_salida(
                        item.id,
                        consumo.c_cantidad,
                        consumo.c_valorUnitario,
                        current_user.id,
                        f"Reasignación #{consumo.id} - {consumo.persona.pe_nombre}"
                    )
                    
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
    
    # Parámetros de filtrado
    buscar = request.args.get('buscar', '').strip()
    tipo = request.args.get('tipo', '')
    fecha_desde = request.args.get('fecha_desde', '')
    fecha_hasta = request.args.get('fecha_hasta', '')
    ordenar = request.args.get('ordenar', 'fecha_desc')
    per_page = int(request.args.get('per_page', 25))
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
            from datetime import datetime
            fecha_desde_obj = datetime.strptime(fecha_desde, '%Y-%m-%d').date()
            query = query.filter(MovimientoDetalle.m_fecha >= fecha_desde_obj)
        except ValueError:
            pass
    
    if fecha_hasta:
        try:
            from datetime import datetime
            fecha_hasta_obj = datetime.strptime(fecha_hasta, '%Y-%m-%d').date()
            query = query.filter(MovimientoDetalle.m_fecha <= fecha_hasta_obj)
        except ValueError:
            pass
    
    # Aplicar ordenamiento
    if ordenar == 'articulo_asc':
        query = query.order_by(asc(Item.i_nombre))
    elif ordenar == 'tipo_asc':
        query = query.order_by(asc(MovimientoDetalle.m_tipo))
    elif ordenar == 'valor_desc':
        query = query.order_by(desc(MovimientoDetalle.m_valorTotal))
    else:  # fecha_desc (por defecto)
        query = query.order_by(desc(MovimientoDetalle.m_fecha), desc(MovimientoDetalle.id))
    
    # Manejar exportaciones
    if export_format in ['excel', 'pdf']:
        movimientos_raw = query.all()
        movimientos_con_stock = _calcular_stock_movimientos(movimientos_raw)
        if export_format == 'excel':
            return _exportar_movimientos_excel(movimientos_con_stock)
        else:
            return _exportar_movimientos_pdf(movimientos_con_stock)
    
    # Paginación
    pagination = query.paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    # Calcular stock anterior y actual para los movimientos paginados
    movimientos_con_stock = _calcular_stock_movimientos(pagination.items)
    
    return render_template('articulos/movimientos.html',
                         movimientos=movimientos_con_stock,
                         pagination=pagination)

def _exportar_movimientos_excel(movimientos):
    """Exporta movimientos a Excel"""
    wb = Workbook()
    ws = wb.active
    ws.title = "Movimientos"
    
    # Configurar orientación horizontal
    ws.page_setup.orientation = ws.ORIENTATION_LANDSCAPE
    
    # Encabezados
    headers = ['Fecha', 'Artículo', 'Código', 'Tipo', 'Cantidad', 'Valor Unit.',
               'Valor Total', 'Usuario', 'Proveedor', 'Observaciones']
    
    # Estilo para encabezados
    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
    header_alignment = Alignment(horizontal="center", vertical="center")
    
    # Escribir encabezados
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_alignment
    
    # Escribir datos
    for row, (movimiento, item, usuario) in enumerate(movimientos, 2):
        # Obtener proveedor si existe
        proveedor_nombre = ""
        if movimiento.e_id and movimiento.entrada and movimiento.entrada.proveedor:
            proveedor_nombre = movimiento.entrada.proveedor.p_razonsocial
        
        ws.cell(row=row, column=1, value=movimiento.m_fecha.strftime('%Y-%m-%d'))
        ws.cell(row=row, column=2, value=item.i_nombre)
        ws.cell(row=row, column=3, value=item.i_codigo)
        ws.cell(row=row, column=4, value=movimiento.m_tipo.title())
        ws.cell(row=row, column=5, value=movimiento.m_cantidad)
        ws.cell(row=row, column=6, value=float(movimiento.m_valorUnitario))
        ws.cell(row=row, column=7, value=float(movimiento.m_valorTotal))
        ws.cell(row=row, column=8, value=usuario.u_username)
        ws.cell(row=row, column=9, value=proveedor_nombre)
        ws.cell(row=row, column=10, value=movimiento.m_observaciones or '')
    
    # Ajustar ancho de columnas
    for column in ws.columns:
        max_length = 0
        column_letter = column[0].column_letter
        for cell in column:
            try:
                if len(str(cell.value)) > max_length:
                    max_length = len(str(cell.value))
            except Exception:
                pass
        adjusted_width = min(max_length + 2, 50)
        ws.column_dimensions[column_letter].width = adjusted_width
    
    # Crear respuesta
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    
    response = make_response(output.read())
    response.headers['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    response.headers['Content-Disposition'] = f'attachment; filename=movimientos_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
    
    return response

def _exportar_movimientos_pdf(movimientos):
    """Exporta movimientos a PDF"""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4),
                          rightMargin=0.5*inch, leftMargin=0.5*inch,
                          topMargin=0.5*inch, bottomMargin=0.5*inch)
    
    elements = []
    styles = getSampleStyleSheet()
    
    # Título
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        spaceAfter=30,
        alignment=1
    )
    
    title = Paragraph("REPORTE DE MOVIMIENTOS DE INVENTARIO", title_style)
    elements.append(title)
    elements.append(Spacer(1, 12))
    
    # Información del reporte
    info_style = ParagraphStyle(
        'InfoStyle',
        parent=styles['Normal'],
        fontSize=10,
        spaceAfter=20
    )
    
    fecha_reporte = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
    info = Paragraph(f"<b>Fecha del reporte:</b> {fecha_reporte}<br/><b>Total de movimientos:</b> {len(movimientos)}", info_style)
    elements.append(info)
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
    
    # Estilo de la tabla
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 7),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    
    elements.append(table)
    
    # Construir PDF
    doc.build(elements)
    buffer.seek(0)
    
    response = make_response(buffer.read())
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename=movimientos_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf'
    
    return response

def _exportar_articulos_excel(articulo, item, movimientos, saldo_calculado):
    """Exporta detalle de artículo a Excel"""
    wb = Workbook()
    ws = wb.active
    ws.title = f"Detalle {item.i_codigo}"
    
    # Configurar orientación horizontal
    ws.page_setup.orientation = ws.ORIENTATION_LANDSCAPE
    
    # Información del artículo
    ws.cell(row=1, column=1, value="DETALLE DE ARTÍCULO").font = Font(bold=True, size=14)
    ws.cell(row=3, column=1, value="Código:").font = Font(bold=True)
    ws.cell(row=3, column=2, value=item.i_codigo)
    ws.cell(row=4, column=1, value="Nombre:").font = Font(bold=True)
    ws.cell(row=4, column=2, value=item.i_nombre)
    ws.cell(row=5, column=1, value="Stock Actual:").font = Font(bold=True)
    ws.cell(row=5, column=2, value=item.i_cantidad)
    ws.cell(row=6, column=1, value="Saldo Calculado:").font = Font(bold=True)
    ws.cell(row=6, column=2, value=saldo_calculado)
    ws.cell(row=7, column=1, value="Valor Unitario:").font = Font(bold=True)
    ws.cell(row=7, column=2, value=float(item.i_vUnitario))
    
    # Encabezados de movimientos
    row_start = 10
    headers = ['Fecha', 'Tipo', 'Cantidad', 'Valor Unit.', 'Valor Total', 'Usuario', 'Observaciones']
    
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=row_start, column=col, value=header)
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
        cell.alignment = Alignment(horizontal="center")
    
    # Datos de movimientos
    for row, mov in enumerate(movimientos, row_start + 1):
        ws.cell(row=row, column=1, value=mov.m_fecha.strftime('%Y-%m-%d'))
        ws.cell(row=row, column=2, value=mov.m_tipo.title())
        ws.cell(row=row, column=3, value=mov.m_cantidad)
        ws.cell(row=row, column=4, value=float(mov.m_valorUnitario))
        ws.cell(row=row, column=5, value=float(mov.m_valorTotal))
        ws.cell(row=row, column=6, value=mov.u_id)
        ws.cell(row=row, column=7, value=mov.m_observaciones or '')
    
    # Ajustar ancho de columnas
    for column in ws.columns:
        max_length = 0
        column_letter = column[0].column_letter
        for cell in column:
            try:
                if len(str(cell.value)) > max_length:
                    max_length = len(str(cell.value))
            except Exception:
                pass
        adjusted_width = min(max_length + 2, 50)
        ws.column_dimensions[column_letter].width = adjusted_width
    
    # Crear respuesta
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    
    response = make_response(output.read())
    response.headers['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    response.headers['Content-Disposition'] = f'attachment; filename=detalle_{item.i_codigo}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
    
    return response

def _exportar_articulos_pdf(articulo, item, movimientos, saldo_calculado):
    """Exporta detalle de artículo a PDF"""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4),
                          rightMargin=0.5*inch, leftMargin=0.5*inch,
                          topMargin=0.5*inch, bottomMargin=0.5*inch)
    
    elements = []
    styles = getSampleStyleSheet()
    
    # Título
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        spaceAfter=30,
        alignment=1
    )
    
    title = Paragraph(f"DETALLE DE ARTÍCULO - {item.i_codigo}", title_style)
    elements.append(title)
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
    ]))
    
    elements.append(info_table)
    elements.append(Spacer(1, 20))
    
    # Título de movimientos
    mov_title = Paragraph("HISTORIAL DE MOVIMIENTOS", styles['Heading2'])
    elements.append(mov_title)
    elements.append(Spacer(1, 12))
    
    # Tabla de movimientos
    mov_data = [['Fecha', 'Tipo', 'Cantidad', 'Valor Unit.', 'Valor Total', 'Observaciones']]
    
    for mov in movimientos[:20]:  # Limitar a 20 movimientos más recientes
        mov_data.append([
            mov.m_fecha.strftime('%Y-%m-%d'),
            mov.m_tipo.title(),
            str(mov.m_cantidad),
            f"${float(mov.m_valorUnitario):.2f}",
            f"${float(mov.m_valorTotal):.2f}",
            (mov.m_observaciones or '')[:30] + '...' if mov.m_observaciones and len(mov.m_observaciones) > 30 else (mov.m_observaciones or '')
        ])
    
    mov_table = Table(mov_data, colWidths=[0.8*inch, 0.8*inch, 0.8*inch, 0.8*inch, 0.8*inch, 2.5*inch])
    mov_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    
    elements.append(mov_table)
    
    # Construir PDF
    doc.build(elements)
    buffer.seek(0)
    
    response = make_response(buffer.read())
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename=detalle_{item.i_codigo}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf'
    
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
    """Exporta el historial de asignaciones a Excel"""
    wb = Workbook()
    ws = wb.active
    ws.title = "Asignaciones"

    headers = ['Fecha', 'Artículo', 'Personal', 'Cantidad', 'Valor Unitario', 'Valor Total', 'Estado', 'Observaciones']
    for col, header in enumerate(headers, 1):
        ws.cell(row=1, column=col, value=header)

    for row, (consumo, persona, item) in enumerate(asignaciones, 2):
        ws.cell(row=row, column=1, value=consumo.c_fecha.strftime('%Y-%m-%d'))
        ws.cell(row=row, column=2, value=item.i_nombre)
        ws.cell(row=row, column=3, value=f"{persona.pe_nombre} {persona.pe_apellido}")
        ws.cell(row=row, column=4, value=consumo.c_cantidad)
        ws.cell(row=row, column=5, value=consumo.c_valorUnitario)
        ws.cell(row=row, column=6, value=consumo.c_valorTotal)
        ws.cell(row=row, column=7, value=consumo.c_estado)
        ws.cell(row=row, column=8, value=consumo.c_observaciones)

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    response = make_response(output.read())
    response.headers['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    response.headers['Content-Disposition'] = f'attachment; filename=asignaciones_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
    return response


def _exportar_asignaciones_pdf(asignaciones):
    """Exporta el historial de asignaciones a PDF"""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4))

    elements = []
    styles = getSampleStyleSheet()
    title = Paragraph("Historial de Asignaciones", styles['Heading1'])
    elements.append(title)

    data = [['Fecha', 'Artículo', 'Personal', 'Cantidad', 'Valor Unitario', 'Valor Total', 'Estado', 'Observaciones']]
    for consumo, persona, item in asignaciones:
        data.append([
            consumo.c_fecha.strftime('%Y-%m-%d'),
            item.i_nombre,
            f"{persona.pe_nombre} {persona.pe_apellido}",
            consumo.c_cantidad,
            f"${consumo.c_valorUnitario:.2f}",
            f"${consumo.c_valorTotal:.2f}",
            consumo.c_estado,
            consumo.c_observaciones or 'Ninguna'
        ])

    table = Table(data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
    ]))
    elements.append(table)

    doc.build(elements)
    buffer.seek(0)
    response = make_response(buffer.read())
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename=asignaciones_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf'
    return response

def _exportar_asignaciones_excel(asignaciones):
    """Exporta el historial de asignaciones a Excel"""
    wb = Workbook()
    ws = wb.active
    ws.title = "Asignaciones"

    headers = ['Fecha', 'Artículo', 'Personal', 'Cantidad', 'Valor Unitario', 'Valor Total', 'Estado', 'Observaciones']
    for col, header in enumerate(headers, 1):
        ws.cell(row=1, column=col, value=header)

    for row, (consumo, persona, item) in enumerate(asignaciones, 2):
        ws.cell(row=row, column=1, value=consumo.c_fecha.strftime('%Y-%m-%d'))
        ws.cell(row=row, column=2, value=item.i_nombre)
        ws.cell(row=row, column=3, value=f"{persona.pe_nombre} {persona.pe_apellido}")
        ws.cell(row=row, column=4, value=consumo.c_cantidad)
        ws.cell(row=row, column=5, value=consumo.c_valorUnitario)
        ws.cell(row=row, column=6, value=consumo.c_valorTotal)
        ws.cell(row=row, column=7, value=consumo.c_estado)
        ws.cell(row=row, column=8, value=consumo.c_observaciones)

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    response = make_response(output.read())
    response.headers['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    response.headers['Content-Disposition'] = f'attachment; filename=asignaciones_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
    return response

def _exportar_asignaciones_pdf(asignaciones):
    """Exporta el historial de asignaciones a PDF"""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4))

    elements = []
    styles = getSampleStyleSheet()
    title = Paragraph("Historial de Asignaciones", styles['Heading1'])
    elements.append(title)

    data = [['Fecha', 'Artículo', 'Personal', 'Cantidad', 'Valor Unitario', 'Valor Total', 'Estado', 'Observaciones']]
    for consumo, persona, item in asignaciones:
        data.append([
            consumo.c_fecha.strftime('%Y-%m-%d'),
            item.i_nombre,
            f"{persona.pe_nombre} {persona.pe_apellido}",
            consumo.c_cantidad,
            f"${consumo.c_valorUnitario:.2f}",
            f"${consumo.c_valorTotal:.2f}",
            consumo.c_estado,
            consumo.c_observaciones or 'Ninguna'
        ])

    table = Table(data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
    ]))
    elements.append(table)

    doc.build(elements)
    buffer.seek(0)
    response = make_response(buffer.read())
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename=asignaciones_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf'
    return response
