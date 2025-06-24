from flask import Blueprint, render_template, request, jsonify, make_response
from flask_login import login_required, current_user
from datetime import datetime, date
from sqlalchemy import func, extract, and_
from app.database.models import (
    MovimientoDetalle, Item, Articulo, Instrumento,
    Proveedor, Persona, Consumo, Entrada
)
from app.database import db
import io
import pandas as pd
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from openpyxl.styles import NamedStyle, Font, PatternFill, Alignment, Border, Side
from reportlab.platypus import HRFlowable
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT


bp = Blueprint('reportes', __name__)

def _mapear_tipo_movimiento(tipo_original):
    """Mapear tipos de movimiento para mostrar solo ingresos y egresos"""
    mapeo = {
        'entrada': 'Ingreso',
        'salida': 'Egreso'
    }
    return mapeo.get(tipo_original, None)  # Retorna None si no es ingreso/egreso

@bp.route('/')
@login_required
def index():
    """Página principal de reportes"""
    return render_template('reportes/index.html')

@bp.route('/generar', methods=['POST'])
@login_required
def generar_reporte():
    """Generar reporte según los parámetros seleccionados"""
    data = request.get_json()
    tipo_reporte = data.get('tipo_reporte')
    periodo = data.get('periodo')
    fecha_inicio = data.get('fecha_inicio')
    fecha_fin = data.get('fecha_fin')
    articulo_id = data.get('articulo_id')
    tipo_item = data.get('tipo_item')
    
    try:
        if tipo_reporte == 'movimientos':
            resultado = _generar_reporte_movimientos(periodo, fecha_inicio, fecha_fin, articulo_id, tipo_item)
        elif tipo_reporte == 'inventario_articulos':
            resultado = _generar_reporte_inventario_articulos()
        elif tipo_reporte == 'inventario_instrumentos':
            resultado = _generar_reporte_inventario_instrumentos()
        elif tipo_reporte == 'proveedores':
            resultado = _generar_reporte_proveedores(periodo, fecha_inicio, fecha_fin)
        elif tipo_reporte == 'consumos':
            resultado = _generar_reporte_consumos(periodo, fecha_inicio, fecha_fin)
        else:
            return jsonify({'error': 'Tipo de reporte no válido'}), 400
            
        return jsonify(resultado)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def _generar_reporte_movimientos(periodo, fecha_inicio, fecha_fin, articulo_id=None, tipo_item=None):
    """Generar reporte de movimientos (ingresos/egresos)"""
    query = db.session.query(
        MovimientoDetalle.m_tipo,
        func.sum(MovimientoDetalle.m_cantidad).label('total_cantidad'),
        func.sum(MovimientoDetalle.m_valorTotal).label('total_valor'),
        func.count(MovimientoDetalle.id).label('total_movimientos')
    )
    
    # Filtrar por tipo de ítem si se especifica
    if tipo_item:
        query = query.join(Item, MovimientoDetalle.i_id == Item.id).filter(Item.i_tipo == tipo_item)
    
    # Filtrar por fechas
    if periodo == 'personalizado' and fecha_inicio and fecha_fin:
        fecha_inicio = datetime.strptime(fecha_inicio, '%Y-%m-%d').date()
        fecha_fin = datetime.strptime(fecha_fin, '%Y-%m-%d').date()
        query = query.filter(MovimientoDetalle.m_fecha.between(fecha_inicio, fecha_fin))
    elif periodo == 'mes_actual':
        hoy = date.today()
        query = query.filter(
            extract('year', MovimientoDetalle.m_fecha) == hoy.year,
            extract('month', MovimientoDetalle.m_fecha) == hoy.month
        )
    elif periodo == 'año_actual':
        hoy = date.today()
        query = query.filter(extract('year', MovimientoDetalle.m_fecha) == hoy.year)
    
    # Filtrar por artículo específico
    if articulo_id:
        query = query.filter(MovimientoDetalle.i_id == articulo_id)
    
    # Agrupar por tipo de movimiento
    movimientos = query.group_by(MovimientoDetalle.m_tipo).all()
    
    # Obtener detalles de movimientos
    query_detalle = db.session.query(
        MovimientoDetalle,
        Item.i_codigo,
        Item.i_nombre,
        Proveedor.p_razonsocial,
        Persona.pe_nombre
    ).join(Item, MovimientoDetalle.i_id == Item.id)\
     .outerjoin(Entrada, MovimientoDetalle.e_id == Entrada.id)\
     .outerjoin(Proveedor, Entrada.p_id == Proveedor.id)\
     .outerjoin(Consumo, MovimientoDetalle.c_id == Consumo.id)\
     .outerjoin(Persona, Consumo.pe_id == Persona.id)
    
    # Filtrar por tipo de ítem si se especifica
    if tipo_item:
        query_detalle = query_detalle.filter(Item.i_tipo == tipo_item)
    
    # Aplicar los mismos filtros de fecha
    if periodo == 'personalizado' and fecha_inicio and fecha_fin:
        query_detalle = query_detalle.filter(MovimientoDetalle.m_fecha.between(fecha_inicio, fecha_fin))
    elif periodo == 'mes_actual':
        hoy = date.today()
        query_detalle = query_detalle.filter(
            extract('year', MovimientoDetalle.m_fecha) == hoy.year,
            extract('month', MovimientoDetalle.m_fecha) == hoy.month
        )
    elif periodo == 'año_actual':
        hoy = date.today()
        query_detalle = query_detalle.filter(extract('year', MovimientoDetalle.m_fecha) == hoy.year)
    
    if articulo_id:
        query_detalle = query_detalle.filter(MovimientoDetalle.i_id == articulo_id)
    
    detalles = query_detalle.order_by(MovimientoDetalle.m_fecha.desc()).limit(50).all()
    
    return {
        'tipo': 'movimientos',
        'resumen': [
            {
                'tipo_movimiento': _mapear_tipo_movimiento(mov.m_tipo),
                'total_cantidad': int(mov.total_cantidad),
                'total_valor': float(mov.total_valor),
                'total_movimientos': mov.total_movimientos
            } for mov in movimientos if _mapear_tipo_movimiento(mov.m_tipo) is not None
        ],
        'detalles': [
            {
                'fecha': mov.m_fecha.strftime('%Y-%m-%d'),
                'tipo': _mapear_tipo_movimiento(mov.m_tipo),
                'codigo_item': codigo,
                'nombre_item': nombre,
                'cantidad': mov.m_cantidad,
                'valor_unitario': float(mov.m_valorUnitario),
                'valor_total': float(mov.m_valorTotal),
                'proveedor': proveedor or 'N/A',
                'persona': persona or 'N/A',
                'observaciones': mov.m_observaciones or ''
            } for mov, codigo, nombre, proveedor, persona in detalles if _mapear_tipo_movimiento(mov.m_tipo) is not None
        ]
    }

def _generar_reporte_inventario_articulos():
    """Generar reporte de inventario de artículos"""
    articulos = db.session.query(
        Item, Articulo
    ).join(Articulo, Item.id == Articulo.i_id)\
     .filter(Item.i_tipo == 'articulo').all()
    
    return {
        'tipo': 'inventario_articulos',
        'articulos': [
            {
                'codigo': item.i_codigo,
                'nombre': item.i_nombre,
                'cantidad': item.i_cantidad,
                'valor_unitario': float(item.i_vUnitario),
                'valor_total': float(item.i_vTotal),
                'stock_min': articulo.a_stockMin,
                'stock_max': articulo.a_stockMax,
                'cuenta_contable': articulo.a_c_contable,
                'estado_stock': 'Bajo' if item.i_cantidad <= articulo.a_stockMin else 'Normal'
            } for item, articulo in articulos
        ]
    }

def _generar_reporte_inventario_instrumentos():
    """Generar reporte de inventario de instrumentos"""
    instrumentos = db.session.query(
        Item, Instrumento
    ).join(Instrumento, Item.id == Instrumento.i_id)\
     .filter(Item.i_tipo == 'instrumento').all()
    
    return {
        'tipo': 'inventario_instrumentos',
        'instrumentos': [
            {
                'codigo': item.i_codigo,
                'nombre': item.i_nombre,
                'marca': instrumento.i_marca,
                'modelo': instrumento.i_modelo,
                'serie': instrumento.i_serie,
                'estado': instrumento.i_estado,
                'valor_unitario': float(item.i_vUnitario),
                'valor_total': float(item.i_vTotal)
            } for item, instrumento in instrumentos
        ]
    }

def _generar_reporte_proveedores(periodo, fecha_inicio, fecha_fin):
    """Generar reporte de proveedores"""
    query = db.session.query(
        Proveedor,
        func.count(Entrada.id).label('total_entradas'),
        func.sum(MovimientoDetalle.m_valorTotal).label('total_compras')
    ).outerjoin(Entrada, Proveedor.id == Entrada.p_id)\
     .outerjoin(MovimientoDetalle, Entrada.id == MovimientoDetalle.e_id)
    
    # Filtrar por fechas
    if periodo == 'personalizado' and fecha_inicio and fecha_fin:
        fecha_inicio = datetime.strptime(fecha_inicio, '%Y-%m-%d').date()
        fecha_fin = datetime.strptime(fecha_fin, '%Y-%m-%d').date()
        query = query.filter(Entrada.e_fecha.between(fecha_inicio, fecha_fin))
    elif periodo == 'mes_actual':
        hoy = date.today()
        query = query.filter(
            extract('year', Entrada.e_fecha) == hoy.year,
            extract('month', Entrada.e_fecha) == hoy.month
        )
    elif periodo == 'año_actual':
        hoy = date.today()
        query = query.filter(extract('year', Entrada.e_fecha) == hoy.year)
    
    proveedores = query.group_by(Proveedor.id).all()
    
    return {
        'tipo': 'proveedores',
        'datos': [
            {
                'codigo': prov.p_codigo,
                'razon_social': prov.p_razonsocial,
                'ci_ruc': prov.p_ci_ruc,
                'direccion': prov.p_direccion or 'N/A',
                'telefono': prov.p_telefono or 'N/A',
                'correo': prov.p_correo or 'N/A',
                'total_entradas': entradas or 0,
                'total_compras': float(compras) if compras else 0.0
            } for prov, entradas, compras in proveedores
        ]
    }

def _generar_reporte_consumos(periodo, fecha_inicio, fecha_fin):
    """Generar reporte de consumos por personas"""
    query = db.session.query(
        Persona,
        func.count(Consumo.id).label('total_consumos'),
        func.sum(MovimientoDetalle.m_cantidad).label('total_cantidad'),
        func.sum(MovimientoDetalle.m_valorTotal).label('total_valor')
    ).outerjoin(Consumo, Persona.id == Consumo.pe_id)\
     .outerjoin(MovimientoDetalle, Consumo.id == MovimientoDetalle.c_id)
    
    # Filtrar por fechas
    if periodo == 'personalizado' and fecha_inicio and fecha_fin:
        fecha_inicio = datetime.strptime(fecha_inicio, '%Y-%m-%d').date()
        fecha_fin = datetime.strptime(fecha_fin, '%Y-%m-%d').date()
        query = query.filter(Consumo.c_fecha.between(fecha_inicio, fecha_fin))
    elif periodo == 'mes_actual':
        hoy = date.today()
        query = query.filter(
            extract('year', Consumo.c_fecha) == hoy.year,
            extract('month', Consumo.c_fecha) == hoy.month
        )
    elif periodo == 'año_actual':
        hoy = date.today()
        query = query.filter(extract('year', Consumo.c_fecha) == hoy.year)
    
    personas = query.group_by(Persona.id).all()
    
    return {
        'tipo': 'consumos',
        'datos': [
            {
                'codigo': pers.pe_codigo,
                'nombre': pers.pe_nombre,
                'total_consumos': consumos or 0,
                'total_cantidad': int(cantidad) if cantidad else 0,
                'total_valor': float(valor) if valor else 0.0
            } for pers, consumos, cantidad, valor in personas
        ]
    }

@bp.route('/articulos-select')
@login_required
def obtener_articulos_select():
    """Obtener lista de artículos para el select"""
    tipo = request.args.get('tipo', '')
    
    query = db.session.query(Item)
    if tipo == 'articulo':
        query = query.filter(Item.i_tipo == 'articulo')
    elif tipo == 'instrumento':
        query = query.filter(Item.i_tipo == 'instrumento')
    # Si no hay tipo específico, devuelve todos los ítems
    
    articulos = query.all()
    return jsonify([
        {
            'id': art.id,
            'codigo': art.i_codigo,
            'nombre': art.i_nombre
        } for art in articulos
    ])

@bp.route('/exportar/excel', methods=['POST'])
@login_required
def exportar_excel():
    """Exportar reporte a Excel con formato profesional"""
    # Obtener datos del formulario
    data = request.form.to_dict()
    tipo_reporte = data.get('tipo_reporte')
    periodo = data.get('periodo')
    fecha_inicio = data.get('fecha_inicio')
    fecha_fin = data.get('fecha_fin')
    articulo_id = data.get('articulo_id')
    tipo_item = data.get('tipo_item')
    orientacion = data.get('orientacion', 'vertical')
    
    try:
        # Generar los datos del reporte
        if tipo_reporte == 'movimientos':
            resultado = _generar_reporte_movimientos(periodo, fecha_inicio, fecha_fin, articulo_id, tipo_item)
        elif tipo_reporte == 'inventario_articulos':
            resultado = _generar_reporte_inventario_articulos()
        elif tipo_reporte == 'inventario_instrumentos':
            resultado = _generar_reporte_inventario_instrumentos()
        elif tipo_reporte == 'proveedores':
            resultado = _generar_reporte_proveedores(periodo, fecha_inicio, fecha_fin)
        elif tipo_reporte == 'consumos':
            resultado = _generar_reporte_consumos(periodo, fecha_inicio, fecha_fin)
        else:
            return jsonify({'error': 'Tipo de reporte no válido'}), 400
        
        # Crear archivo Excel con formato profesional
        output = io.BytesIO()
        
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            # Obtener workbook y crear estilos
            workbook = writer.book
            
            # Definir estilos profesionales
            header_style = NamedStyle(name="header_style")
            header_style.font = Font(name='Calibri', size=12, bold=True, color="FFFFFF")
            header_style.fill = PatternFill(start_color="2E5984", end_color="2E5984", fill_type="solid")
            header_style.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
            header_style.border = Border(
                left=Side(style='thin'), right=Side(style='thin'),
                top=Side(style='thin'), bottom=Side(style='thin')
            )
            
            title_style = NamedStyle(name="title_style")
            title_style.font = Font(name='Calibri', size=16, bold=True, color="2E5984")
            title_style.alignment = Alignment(horizontal="center", vertical="center")
            
            subtitle_style = NamedStyle(name="subtitle_style")
            subtitle_style.font = Font(name='Calibri', size=12, bold=True, color="4472C4")
            subtitle_style.alignment = Alignment(horizontal="center", vertical="center")
            
            data_style = NamedStyle(name="data_style")
            data_style.font = Font(name='Calibri', size=10)
            data_style.alignment = Alignment(horizontal="center", vertical="center")
            data_style.border = Border(
                left=Side(style='thin'), right=Side(style='thin'),
                top=Side(style='thin'), bottom=Side(style='thin')
            )
            
            currency_style = NamedStyle(name="currency_style")
            currency_style.font = Font(name='Calibri', size=10)
            currency_style.alignment = Alignment(horizontal="right", vertical="center")
            currency_style.number_format = '"$"#,##0.00_);("$"#,##0.00)'
            currency_style.border = Border(
                left=Side(style='thin'), right=Side(style='thin'),
                top=Side(style='thin'), bottom=Side(style='thin')
            )
            
            # Registrar estilos
            try:
                workbook.add_named_style(header_style)
                workbook.add_named_style(title_style)
                workbook.add_named_style(subtitle_style)
                workbook.add_named_style(data_style)
                workbook.add_named_style(currency_style)
            except ValueError:
                pass  # Los estilos ya existen
            
            # Crear hoja de portada
            _crear_portada_excel(writer, tipo_reporte, periodo, fecha_inicio, fecha_fin, articulo_id, tipo_item, orientacion)
            
            # Agregar datos según el tipo de reporte
            if tipo_reporte == 'movimientos':
                if resultado.get('resumen'):
                    _crear_hoja_resumen_movimientos(writer, resultado['resumen'])
                
                if resultado.get('detalles'):
                    _crear_hoja_detalles_movimientos(writer, resultado['detalles'])
            
            elif tipo_reporte == 'inventario_articulos':
                if resultado.get('articulos'):
                    _crear_hoja_inventario_articulos(writer, resultado['articulos'])
            
            elif tipo_reporte == 'inventario_instrumentos':
                if resultado.get('instrumentos'):
                    _crear_hoja_inventario_instrumentos(writer, resultado['instrumentos'])
            
            elif tipo_reporte == 'proveedores':
                _crear_hoja_proveedores(writer, resultado['datos'])
            
            elif tipo_reporte == 'consumos':
                _crear_hoja_consumos(writer, resultado['datos'])
        
        output.seek(0)
        
        # Crear respuesta
        response = make_response(output.getvalue())
        response.headers['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        response.headers['Content-Disposition'] = f'attachment; filename=CNM_Reporte_{tipo_reporte.title()}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
        
        return response
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/exportar/pdf', methods=['POST'])
@login_required
def exportar_pdf():
    """Exportar reporte a PDF con diseño profesional"""
    # Obtener datos del formulario
    data = request.form.to_dict()
    tipo_reporte = data.get('tipo_reporte')
    periodo = data.get('periodo')
    fecha_inicio = data.get('fecha_inicio')
    fecha_fin = data.get('fecha_fin')
    articulo_id = data.get('articulo_id')
    tipo_item = data.get('tipo_item')
    orientacion = data.get('orientacion', 'vertical')
    
    try:
        # Generar los datos del reporte
        if tipo_reporte == 'movimientos':
            resultado = _generar_reporte_movimientos(periodo, fecha_inicio, fecha_fin, articulo_id, tipo_item)
        elif tipo_reporte == 'inventario_articulos':
            resultado = _generar_reporte_inventario_articulos()
        elif tipo_reporte == 'inventario_instrumentos':
            resultado = _generar_reporte_inventario_instrumentos()
        elif tipo_reporte == 'proveedores':
            resultado = _generar_reporte_proveedores(periodo, fecha_inicio, fecha_fin)
        elif tipo_reporte == 'consumos':
            resultado = _generar_reporte_consumos(periodo, fecha_inicio, fecha_fin)
        else:
            return jsonify({'error': 'Tipo de reporte no válido'}), 400
        
        # Crear archivo PDF con diseño profesional
        buffer = io.BytesIO()
        
        # Determinar orientación y tamaño de página
        if orientacion == 'horizontal':
            from reportlab.lib.pagesizes import landscape
            pagesize = landscape(A4)
            rightMargin = inch*0.5
            leftMargin = inch*0.5
            topMargin = inch*0.75
            bottomMargin = inch*0.5
        else:
            pagesize = A4
            rightMargin = inch*0.75
            leftMargin = inch*0.75
            topMargin = inch*1
            bottomMargin = inch*0.75
        
        doc = SimpleDocTemplate(
            buffer,
            pagesize=pagesize,
            rightMargin=rightMargin,
            leftMargin=leftMargin,
            topMargin=topMargin,
            bottomMargin=bottomMargin
        )
        elements = []
        
        # Definir estilos profesionales
        styles = _crear_estilos_profesionales()
        
        # Crear encabezado institucional
        elements.extend(_crear_encabezado_institucional(styles))
        
        # Información del reporte
        encabezado_data = _crear_encabezado_reporte(tipo_reporte, periodo, fecha_inicio, fecha_fin, articulo_id, tipo_item)
        elements.extend(_crear_informacion_reporte(encabezado_data, styles))
        
        # Contenido según tipo de reporte
        if tipo_reporte == 'movimientos' and resultado.get('detalles'):
            elements.extend(_crear_contenido_movimientos_pdf(resultado, styles))
        elif tipo_reporte == 'inventario_articulos':
            elements.extend(_crear_contenido_inventario_articulos_pdf(resultado, styles))
        elif tipo_reporte == 'inventario_instrumentos':
            elements.extend(_crear_contenido_inventario_instrumentos_pdf(resultado, styles))
        elif tipo_reporte == 'proveedores':
            elements.extend(_crear_contenido_proveedores_pdf(resultado, styles))
        elif tipo_reporte == 'consumos':
            elements.extend(_crear_contenido_consumos_pdf(resultado, styles))
        
        # Agregar pie de página
        elements.extend(_crear_pie_pagina(styles))
        
        # Construir PDF
        doc.build(elements, onFirstPage=_agregar_numero_pagina, onLaterPages=_agregar_numero_pagina)
        buffer.seek(0)
        
        # Crear respuesta
        response = make_response(buffer.getvalue())
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'attachment; filename=CNM_Reporte_{tipo_reporte.title()}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf'
        
        return response
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# Funciones auxiliares para Excel
def _crear_portada_excel(writer, tipo_reporte, periodo, fecha_inicio, fecha_fin, articulo_id, tipo_item=None, orientacion='vertical'):
    """Crear hoja de portada profesional para Excel"""
    ws = writer.book.create_worksheet("Información General")
    
    # Logo y encabezado institucional
    ws['B2'] = "CONSERVATORIO NACIONAL DE MÚSICA"
    ws['B2'].style = "title_style"
    ws.merge_cells('B2:G2')
    
    ws['B3'] = "Sistema de Gestión de Inventario"
    ws['B3'].style = "subtitle_style"
    ws.merge_cells('B3:G3')
    
    ws['B4'] = "Cochapata E12-56, Quito - Ecuador"
    ws['B4'].font = Font(name='Calibri', size=10, italic=True)
    ws['B4'].alignment = Alignment(horizontal="center")
    ws.merge_cells('B4:G4')
    
    # Información del reporte
    row = 7
    ws[f'B{row}'] = "INFORMACIÓN DEL REPORTE"
    ws[f'B{row}'].style = "subtitle_style"
    ws.merge_cells(f'B{row}:G{row}')
    
    row += 2
    
    # Determinar el tipo de reporte con información específica
    tipo_reporte_texto = tipo_reporte.replace('_', ' ').title()
    if tipo_reporte == 'movimientos' and tipo_item:
        if tipo_item == 'articulo':
            tipo_reporte_texto = 'Movimientos - Solo Artículos'
        elif tipo_item == 'instrumento':
            tipo_reporte_texto = 'Movimientos - Solo Instrumentos'
        else:
            tipo_reporte_texto = 'Movimientos - Todos los Ítems'
    elif tipo_reporte == 'movimientos':
        tipo_reporte_texto = 'Movimientos - Todos los Ítems'
    
    info_data = [
        ["Tipo de Reporte:", tipo_reporte_texto],
        ["Generado por:", current_user.username if current_user.is_authenticated else 'Sistema'],
        ["Fecha de Generación:", datetime.now().strftime('%d/%m/%Y')],
        ["Hora de Generación:", datetime.now().strftime('%H:%M:%S')],
        ["Período:", periodo.replace('_', ' ').title()],
        ["Orientación:", "Horizontal (Landscape)" if orientacion == 'horizontal' else "Vertical (Portrait)"],
    ]
    
    if periodo == 'personalizado' and fecha_inicio and fecha_fin:
        info_data.extend([
            ["Fecha Inicio:", fecha_inicio],
            ["Fecha Fin:", fecha_fin]
        ])
    
    for label, value in info_data:
        ws[f'B{row}'] = label
        ws[f'B{row}'].font = Font(name='Calibri', size=11, bold=True)
        ws[f'C{row}'] = value
        ws[f'C{row}'].font = Font(name='Calibri', size=11)
        row += 1
    
    # Ajustar anchos de columna
    ws.column_dimensions['B'].width = 20
    ws.column_dimensions['C'].width = 25


def _crear_hoja_detalles_movimientos(writer, detalles):
    """Crear hoja de detalles de movimientos con formato profesional"""
    df = pd.DataFrame(detalles)
    df.to_excel(writer, sheet_name='Detalle de Movimientos', index=False, startrow=1)
    
    ws = writer.sheets['Detalle de Movimientos']
    
    # Título de la hoja
    ws['A1'] = "DETALLE DE MOVIMIENTOS DE INVENTARIO"
    ws['A1'].style = "subtitle_style"
    ws.merge_cells('A1:H1')
    
    # Aplicar estilos a encabezados
    for col_num, column_title in enumerate(df.columns, 1):
        cell = ws.cell(row=2, column=col_num)
        cell.value = column_title.replace('_', ' ').title()
        cell.style = "header_style"
    
    # Aplicar estilos a datos
    for row_num in range(3, len(df) + 3):
        for col_num in range(1, len(df.columns) + 1):
            cell = ws.cell(row=row_num, column=col_num)
            if 'valor' in df.columns[col_num-1].lower() or 'precio' in df.columns[col_num-1].lower():
                cell.style = "currency_style"
            else:
                cell.style = "data_style"
    
    # Ajustar anchos de columna
    for column in ws.columns:
        max_length = max(len(str(cell.value)) for cell in column)
        ws.column_dimensions[column[0].column_letter].width = min(max_length + 2, 50)


def _crear_hoja_resumen_movimientos(writer, resumen):
    """Crear hoja de resumen de movimientos"""
    df = pd.DataFrame(resumen)
    df.to_excel(writer, sheet_name='Resumen Movimientos', index=False, startrow=1)
    
    ws = writer.sheets['Resumen Movimientos']
    ws['A1'] = "RESUMEN DE MOVIMIENTOS POR TIPO"
    ws['A1'].style = "subtitle_style"
    ws.merge_cells('A1:D1')
    
    # Aplicar estilos
    for col_num, column_title in enumerate(df.columns, 1):
        cell = ws.cell(row=2, column=col_num)
        cell.value = column_title.replace('_', ' ').title()
        cell.style = "header_style"
    
    for row_num in range(3, len(df) + 3):
        for col_num in range(1, len(df.columns) + 1):
            cell = ws.cell(row=row_num, column=col_num)
            if 'valor' in df.columns[col_num-1].lower():
                cell.style = "currency_style"
            else:
                cell.style = "data_style"

def _crear_hoja_inventario_articulos(writer, articulos):
    """Crear hoja de inventario de artículos"""
    df = pd.DataFrame(articulos)
    df.to_excel(writer, sheet_name='Inventario Artículos', index=False, startrow=1)
    
    ws = writer.sheets['Inventario Artículos']
    ws['A1'] = "INVENTARIO DE ARTÍCULOS"
    ws['A1'].style = "subtitle_style"
    ws.merge_cells('A1:I1')
    
    # Aplicar estilos
    for col_num, column_title in enumerate(df.columns, 1):
        cell = ws.cell(row=2, column=col_num)
        cell.value = column_title.replace('_', ' ').title()
        cell.style = "header_style"
    
    for row_num in range(3, len(df) + 3):
        for col_num in range(1, len(df.columns) + 1):
            cell = ws.cell(row=row_num, column=col_num)
            if 'valor' in df.columns[col_num-1].lower():
                cell.style = "currency_style"
            else:
                cell.style = "data_style"

def _crear_hoja_inventario_instrumentos(writer, instrumentos):
    """Crear hoja de inventario de instrumentos"""
    df = pd.DataFrame(instrumentos)
    df.to_excel(writer, sheet_name='Inventario Instrumentos', index=False, startrow=1)
    
    ws = writer.sheets['Inventario Instrumentos']
    ws['A1'] = "INVENTARIO DE INSTRUMENTOS"
    ws['A1'].style = "subtitle_style"
    ws.merge_cells('A1:H1')
    
    # Aplicar estilos
    for col_num, column_title in enumerate(df.columns, 1):
        cell = ws.cell(row=2, column=col_num)
        cell.value = column_title.replace('_', ' ').title()
        cell.style = "header_style"
    
    for row_num in range(3, len(df) + 3):
        for col_num in range(1, len(df.columns) + 1):
            cell = ws.cell(row=row_num, column=col_num)
            if 'valor' in df.columns[col_num-1].lower():
                cell.style = "currency_style"
            else:
                cell.style = "data_style"

def _crear_hoja_proveedores(writer, proveedores):
    """Crear hoja de proveedores"""
    df = pd.DataFrame(proveedores)
    df.to_excel(writer, sheet_name='Proveedores', index=False, startrow=1)
    
    ws = writer.sheets['Proveedores']
    ws['A1'] = "REPORTE DE PROVEEDORES"
    ws['A1'].style = "subtitle_style"
    ws.merge_cells('A1:H1')
    
    # Aplicar estilos
    for col_num, column_title in enumerate(df.columns, 1):
        cell = ws.cell(row=2, column=col_num)
        cell.value = column_title.replace('_', ' ').title()
        cell.style = "header_style"
    
    for row_num in range(3, len(df) + 3):
        for col_num in range(1, len(df.columns) + 1):
            cell = ws.cell(row=row_num, column=col_num)
            if 'compras' in df.columns[col_num-1].lower():
                cell.style = "currency_style"
            else:
                cell.style = "data_style"

def _crear_hoja_consumos(writer, consumos):
    """Crear hoja de consumos"""
    df = pd.DataFrame(consumos)
    df.to_excel(writer, sheet_name='Consumos', index=False, startrow=1)
    
    ws = writer.sheets['Consumos']
    ws['A1'] = "REPORTE DE CONSUMOS POR PERSONAS"
    ws['A1'].style = "subtitle_style"
    ws.merge_cells('A1:E1')
    
    # Aplicar estilos
    for col_num, column_title in enumerate(df.columns, 1):
        cell = ws.cell(row=2, column=col_num)
        cell.value = column_title.replace('_', ' ').title()
        cell.style = "header_style"
    
    for row_num in range(3, len(df) + 3):
        for col_num in range(1, len(df.columns) + 1):
            cell = ws.cell(row=row_num, column=col_num)
            if 'valor' in df.columns[col_num-1].lower():
                cell.style = "currency_style"
            else:
                cell.style = "data_style"

# Funciones auxiliares para PDF
def _crear_estilos_profesionales():
    """Crear estilos profesionales para PDF"""
    styles = getSampleStyleSheet()
    
    # Estilo para título principal
    styles.add(ParagraphStyle(
        name='TituloInstitucional',
        parent=styles['Title'],
        fontSize=18,
        fontName='Helvetica-Bold',
        textColor=colors.HexColor('#2E5984'),
        alignment=1,
        spaceAfter=10
    ))
    
    # Estilo para subtítulo
    styles.add(ParagraphStyle(
        name='SubtituloInstitucional',
        parent=styles['Normal'],
        fontSize=12,
        fontName='Helvetica',
        textColor=colors.HexColor('#4472C4'),
        alignment=1,
        spaceAfter=20
    ))
    
    # Estilo para títulos de sección
    styles.add(ParagraphStyle(
        name='TituloSeccion',
        parent=styles['Heading2'],
        fontSize=14,
        fontName='Helvetica-Bold',
        textColor=colors.HexColor('#2E5984'),
        spaceBefore=20,
        spaceAfter=12,
        leftIndent=0,
        backColor=colors.HexColor('#F8F9FA'),
        borderWidth=1,
        borderColor=colors.HexColor('#2E5984'),
        borderPadding=8
    ))
    
    # Estilo para información
    styles.add(ParagraphStyle(
        name='Informacion',
        parent=styles['Normal'],
        fontSize=10,
        fontName='Helvetica',
        leftIndent=20,
        spaceAfter=6
    ))
    
    return styles


def _crear_encabezado_institucional(styles):
    """Crear encabezado institucional profesional"""
    elements = []
    
    # Logo placeholder y título
    elements.append(Paragraph("CONSERVATORIO NACIONAL DE MÚSICA", styles['TituloInstitucional']))
    elements.append(Paragraph("Cochapata E12-56, Quito - Ecuador", styles['SubtituloInstitucional']))
    
    # Línea decorativa usando tabla
    line_table = Table([['_' * 60]], colWidths=[7.5*inch])
    line_table.setStyle(TableStyle([
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#2E5984')),
        ('FONTSIZE', (0, 0), (-1, -1), 12),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
    ]))
    elements.append(Spacer(1, 10))
    elements.append(line_table)
    elements.append(Spacer(1, 20))
    
    return elements


def _crear_informacion_reporte(encabezado_data, styles):
    """Crear sección de información del reporte"""
    elements = []
    
    elements.append(Paragraph("INFORMACIÓN DEL REPORTE", styles['TituloSeccion']))
    
    # Tabla de información en formato profesional
    info_data = [
        ['Tipo de Reporte:', encabezado_data.get('categoria', 'N/A'), 
         'Usuario:', encabezado_data.get('usuario', 'N/A')],
        ['Período Desde:', encabezado_data.get('fecha_inicio', 'N/A'),
         'Período Hasta:', encabezado_data.get('fecha_fin', 'N/A')],
        ['Fecha de Generación:', encabezado_data.get('fecha_impresion', 'N/A'),
         'Valor Total:', encabezado_data.get('total', 'N/A')]
    ]
    
    info_table = Table(info_data, colWidths=[1.8*inch, 2.2*inch, 1.5*inch, 2*inch])
    info_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F8F9FA')),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('PADDING', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#D1D5DB')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#2E5984')),
        ('TEXTCOLOR', (2, 0), (2, -1), colors.HexColor('#2E5984')),
    ]))
    
    elements.append(info_table)
    elements.append(Spacer(1, 30))
    
    return elements


def _crear_contenido_movimientos_pdf(resultado, styles):
    """Crear contenido de movimientos para PDF"""
    elements = []
    
    if resultado.get('detalles'):
        elements.append(Paragraph("DETALLE DE MOVIMIENTOS", styles['TituloSeccion']))
        
        # Tabla de movimientos con mejor formato
        headers = ['Fecha', 'Tipo', 'Código', 'Artículo', 'Cant.', 'V. Unit.', 'V. Total']
        data = [headers]
        
        for detalle in resultado['detalles'][:40]:  # Limitar registros
            data.append([
                detalle.get('fecha', 'N/A'),
                detalle.get('tipo', 'N/A').upper(),
                detalle.get('codigo_item', 'N/A'),
                (detalle.get('nombre_item', 'N/A')[:25] + '...' 
                 if len(detalle.get('nombre_item', '')) > 25 
                 else detalle.get('nombre_item', 'N/A')),
                str(detalle.get('cantidad', 0)),
                f"${detalle.get('valor_unitario', 0):.2f}",
                f"${detalle.get('valor_total', 0):.2f}"
            ])
        
        table = Table(data, colWidths=[0.9*inch, 0.8*inch, 0.9*inch, 2.2*inch, 0.6*inch, 0.8*inch, 0.8*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2E5984')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('ALIGN', (3, 1), (3, -1), 'LEFT'),  # Alinear nombres a la izquierda
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('PADDING', (0, 0), (-1, -1), 6),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#FAFAFA')),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#D1D5DB')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F9F9F9')])
        ]))
        
        elements.append(table)
    
    return elements


def _crear_pie_pagina(styles):
    """Crear pie de página profesional"""
    elements = []
    
    elements.append(Spacer(1, 30))
    
    # Crear línea separadora manualmente
    line_table = Table([['_' * 80]], colWidths=[7.5*inch])
    line_table.setStyle(TableStyle([
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#D1D5DB')),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
    ]))
    elements.append(line_table)
    
    elements.append(Spacer(1, 10))
    
    pie_texto = f"""
    <para align="center" fontsize="8" textColor="#6B7280">
    Conservatorio Nacional de Música - Sistema de Gestión de Inventario<br/>
    Generado el {datetime.now().strftime('%d/%m/%Y a las %H:%M:%S')}<br/>
    Documento confidencial - Solo para uso interno
    </para>
    """
    
    elements.append(Paragraph(pie_texto, styles['Normal']))
    
    return elements


def _agregar_numero_pagina(canvas, doc):
    """Agregar número de página"""
    canvas.saveState()
    canvas.setFont('Helvetica', 8)
    canvas.setFillColor(colors.HexColor('#6B7280'))
    canvas.drawRightString(
        doc.pagesize[0] - 0.75*inch, 
        0.5*inch, 
        f"Página {doc.page}"
    )
    canvas.restoreState()


def _crear_encabezado_reporte(tipo_reporte, periodo, fecha_inicio, fecha_fin, articulo_id=None, tipo_item=None):
    """Crear datos del encabezado para el reporte (versión mejorada)"""
    
    # Determinar la categoría del reporte con información del tipo de ítem
    categoria = tipo_reporte.replace('_', ' ').title()
    if tipo_reporte == 'movimientos' and tipo_item:
        if tipo_item == 'articulo':
            categoria = 'Movimientos - Solo Artículos'
        elif tipo_item == 'instrumento':
            categoria = 'Movimientos - Solo Instrumentos'
        else:
            categoria = 'Movimientos - Todos los Ítems'
    elif tipo_reporte == 'movimientos':
        categoria = 'Movimientos - Todos los Ítems'
    
    encabezado = {
        'conservatorio': 'Conservatorio Nacional de Música',
        'direccion': 'Cochapata E12-56, Quito - Ecuador',
        'usuario': current_user.username if current_user.is_authenticated else 'Sistema',
        'fecha_impresion': datetime.now().strftime('%d/%m/%Y %H:%M:%S'),
        'categoria': categoria
    }
    
    # Determinar fechas con mejor formato
    if periodo == 'personalizado' and fecha_inicio and fecha_fin:
        encabezado['fecha_inicio'] = datetime.strptime(fecha_inicio, '%Y-%m-%d').strftime('%d/%m/%Y')
        encabezado['fecha_fin'] = datetime.strptime(fecha_fin, '%Y-%m-%d').strftime('%d/%m/%Y')
    elif periodo == 'mes_actual':
        hoy = date.today()
        primer_dia = date(hoy.year, hoy.month, 1)
        encabezado['fecha_inicio'] = primer_dia.strftime('%d/%m/%Y')
        encabezado['fecha_fin'] = hoy.strftime('%d/%m/%Y')
    elif periodo == 'año_actual':
        hoy = date.today()
        primer_dia = date(hoy.year, 1, 1)
        encabezado['fecha_inicio'] = primer_dia.strftime('%d/%m/%Y')
        encabezado['fecha_fin'] = hoy.strftime('%d/%m/%Y')
    else:
        encabezado['fecha_inicio'] = 'No especificado'
        encabezado['fecha_fin'] = 'No especificado'
    
    # Calcular total con mejor formato
    total_valor = 0.0
    try:
        if tipo_reporte == 'movimientos':
            resultado = _generar_reporte_movimientos(periodo, fecha_inicio, fecha_fin, articulo_id)
            if resultado.get('resumen'):
                total_valor = sum(item.get('total_valor', 0) for item in resultado['resumen'])
        elif tipo_reporte == 'inventario_articulos':
            resultado = _generar_reporte_inventario_articulos()
            if resultado.get('articulos'):
                total_valor = sum(art.get('valor_total', 0) for art in resultado['articulos'])
        elif tipo_reporte == 'inventario_instrumentos':
            resultado = _generar_reporte_inventario_instrumentos()
            if resultado.get('instrumentos'):
                total_valor = sum(inst.get('valor_total', 0) for inst in resultado['instrumentos'])
        elif tipo_reporte == 'proveedores':
            resultado = _generar_reporte_proveedores(periodo, fecha_inicio, fecha_fin)
            if resultado.get('datos'):
                total_valor = sum(prov.get('total_compras', 0) for prov in resultado['datos'])
        elif tipo_reporte == 'consumos':
            resultado = _generar_reporte_consumos(periodo, fecha_inicio, fecha_fin)
            if resultado.get('datos'):
                total_valor = sum(cons.get('total_valor', 0) for cons in resultado['datos'])
    except Exception as e:
        print(f"Error calculando total: {e}")
        total_valor = 0.0
    
    encabezado['total'] = f"${total_valor:,.2f}"
    
    return encabezado

def _crear_contenido_inventario_articulos_pdf(resultado, styles):
    """Crear contenido de inventario de artículos para PDF"""
    elements = []
    
    if resultado.get('articulos'):
        elements.append(Paragraph("INVENTARIO DE ARTÍCULOS", styles['TituloSeccion']))
        
        headers = ['Código', 'Nombre', 'Cantidad', 'Stock Mín.', 'Valor Unit.', 'Estado']
        data = [headers]
        
        for articulo in resultado['articulos'][:30]:
            data.append([
                articulo.get('codigo', 'N/A'),
                (articulo.get('nombre', 'N/A')[:25] + '...'
                 if len(articulo.get('nombre', '')) > 25
                 else articulo.get('nombre', 'N/A')),
                str(articulo.get('cantidad', 0)),
                str(articulo.get('stock_min', 0)),
                f"${articulo.get('valor_unitario', 0):.2f}",
                articulo.get('estado_stock', 'N/A')
            ])
        
        table = Table(data, colWidths=[1*inch, 2.5*inch, 0.8*inch, 0.8*inch, 1*inch, 0.8*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2E5984')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('ALIGN', (1, 1), (1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('PADDING', (0, 0), (-1, -1), 6),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#FAFAFA')),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#D1D5DB')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F9F9F9')])
        ]))
        
        elements.append(table)
    
    return elements

def _crear_contenido_inventario_instrumentos_pdf(resultado, styles):
    """Crear contenido de inventario de instrumentos para PDF"""
    elements = []
    
    if resultado.get('instrumentos'):
        elements.append(Paragraph("INVENTARIO DE INSTRUMENTOS", styles['TituloSeccion']))
        
        headers = ['Código', 'Nombre', 'Marca', 'Modelo', 'Serie', 'Estado', 'Valor Unit.']
        data = [headers]
        
        for instrumento in resultado['instrumentos'][:30]:
            data.append([
                instrumento.get('codigo', 'N/A'),
                (instrumento.get('nombre', 'N/A')[:20] + '...'
                 if len(instrumento.get('nombre', '')) > 20
                 else instrumento.get('nombre', 'N/A')),
                instrumento.get('marca', 'N/A'),
                instrumento.get('modelo', 'N/A'),
                instrumento.get('serie', 'N/A'),
                instrumento.get('estado', 'N/A'),
                f"${instrumento.get('valor_unitario', 0):.2f}"
            ])
        
        table = Table(data, colWidths=[0.8*inch, 1.8*inch, 1*inch, 1*inch, 1*inch, 0.8*inch, 1*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2E5984')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('ALIGN', (1, 1), (1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('PADDING', (0, 0), (-1, -1), 6),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#FAFAFA')),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#D1D5DB')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F9F9F9')])
        ]))
        
        elements.append(table)
    
    return elements

def _crear_contenido_inventario_pdf(resultado, styles):
    """Crear contenido de inventario para PDF"""
    elements = []
    
    if resultado.get('articulos'):
        elements.append(Paragraph("INVENTARIO DE ARTÍCULOS", styles['TituloSeccion']))
        
        headers = ['Código', 'Nombre', 'Cantidad', 'Stock Mín.', 'Valor Unit.', 'Estado']
        data = [headers]
        
        for articulo in resultado['articulos'][:30]:
            data.append([
                articulo.get('codigo', 'N/A'),
                (articulo.get('nombre', 'N/A')[:25] + '...'
                 if len(articulo.get('nombre', '')) > 25
                 else articulo.get('nombre', 'N/A')),
                str(articulo.get('cantidad', 0)),
                str(articulo.get('stock_min', 0)),
                f"${articulo.get('valor_unitario', 0):.2f}",
                articulo.get('estado_stock', 'N/A')
            ])
        
        table = Table(data, colWidths=[1*inch, 2.5*inch, 0.8*inch, 0.8*inch, 1*inch, 0.8*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2E5984')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('ALIGN', (1, 1), (1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('PADDING', (0, 0), (-1, -1), 6),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#FAFAFA')),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#D1D5DB')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F9F9F9')])
        ]))
        
        elements.append(table)
    
    return elements

def _crear_contenido_proveedores_pdf(resultado, styles):
    """Crear contenido de proveedores para PDF"""
    elements = []
    
    if resultado.get('datos'):
        elements.append(Paragraph("REPORTE DE PROVEEDORES", styles['TituloSeccion']))
        
        headers = ['Código', 'Razón Social', 'CI/RUC', 'Teléfono', 'Total Entradas', 'Total Compras']
        data = [headers]
        
        for proveedor in resultado['datos'][:30]:
            data.append([
                proveedor.get('codigo', 'N/A'),
                (proveedor.get('razon_social', 'N/A')[:20] + '...'
                 if len(proveedor.get('razon_social', '')) > 20
                 else proveedor.get('razon_social', 'N/A')),
                proveedor.get('ci_ruc', 'N/A'),
                proveedor.get('telefono', 'N/A'),
                str(proveedor.get('total_entradas', 0)),
                f"${proveedor.get('total_compras', 0):.2f}"
            ])
        
        table = Table(data, colWidths=[0.8*inch, 2*inch, 1*inch, 1*inch, 0.8*inch, 1*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2E5984')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('ALIGN', (1, 1), (1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('PADDING', (0, 0), (-1, -1), 6),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#FAFAFA')),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#D1D5DB')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F9F9F9')])
        ]))
        
        elements.append(table)
    
    return elements

def _crear_contenido_consumos_pdf(resultado, styles):
    """Crear contenido de consumos para PDF"""
    elements = []
    
    if resultado.get('datos'):
        elements.append(Paragraph("REPORTE DE CONSUMOS POR PERSONAS", styles['TituloSeccion']))
        
        headers = ['Código', 'Nombre', 'Total Consumos', 'Total Cantidad', 'Total Valor']
        data = [headers]
        
        for persona in resultado['datos'][:30]:
            data.append([
                persona.get('codigo', 'N/A'),
                (persona.get('nombre', 'N/A')[:25] + '...'
                 if len(persona.get('nombre', '')) > 25
                 else persona.get('nombre', 'N/A')),
                str(persona.get('total_consumos', 0)),
                str(persona.get('total_cantidad', 0)),
                f"${persona.get('total_valor', 0):.2f}"
            ])
        
        table = Table(data, colWidths=[1*inch, 2.5*inch, 1*inch, 1*inch, 1*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2E5984')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('ALIGN', (1, 1), (1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('PADDING', (0, 0), (-1, -1), 6),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#FAFAFA')),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#D1D5DB')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F9F9F9')])
        ]))
        
        elements.append(table)
    
    return elements