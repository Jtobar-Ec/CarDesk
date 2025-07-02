from flask import Blueprint, render_template, request, jsonify, make_response
from flask_login import login_required, current_user
from datetime import datetime, date
from sqlalchemy import func, extract, and_
from app.database.models import (
    MovimientoDetalle, Item, Articulo, Instrumento,
    Proveedor, Persona, Consumo, Entrada, Usuario
)
from app.database import db
from app.utils.export_utils import (
    crear_cabecera_excel, crear_estilos_excel, ajustar_columnas_excel,
    crear_cabecera_pdf, crear_estilos_pdf, aplicar_estilo_tabla_pdf
)
import io
from openpyxl import Workbook
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.units import inch
from reportlab.lib import colors

bp = Blueprint('reportes', __name__)

def _mapear_tipo_movimiento(tipo_original):
    """Mapear tipos de movimiento para mostrar solo ingresos y egresos"""
    mapeo = {
        'entrada': 'Ingreso',
        'salida': 'Egreso'
    }
    return mapeo.get(tipo_original, None)

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
    """Exportar reporte a Excel con cabecera institucional estandarizada"""
    data = request.form.to_dict()
    tipo_reporte = data.get('tipo_reporte')
    periodo = data.get('periodo')
    fecha_inicio = data.get('fecha_inicio')
    fecha_fin = data.get('fecha_fin')
    articulo_id = data.get('articulo_id')
    tipo_item = data.get('tipo_item')
    
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
        
        # Crear archivo Excel
        output = io.BytesIO()
        workbook = Workbook()
        ws = workbook.active
        ws.title = f"Reporte {tipo_reporte.title()}"
        
        # Crear cabecera institucional estandarizada
        current_row = crear_cabecera_excel(
            ws,
            f"Reporte de {tipo_reporte.replace('_', ' ').title()}",
            current_user.username if current_user.is_authenticated else 'Sistema'
        )
        
        # Crear reporte completo
        _crear_reporte_completo_optimizado(ws, tipo_reporte, periodo, fecha_inicio, fecha_fin, resultado, current_row)
        
        # Ajustar columnas
        ajustar_columnas_excel(ws)
        
        # Guardar workbook
        workbook.save(output)
        output.seek(0)
        
        # Crear respuesta
        response = make_response(output.getvalue())
        response.headers['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        response.headers['Content-Disposition'] = f'attachment; filename=CNM_Reporte_{tipo_reporte.title()}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
        
        return response
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def _crear_reporte_completo_optimizado(ws, tipo_reporte, periodo, fecha_inicio, fecha_fin, resultado, current_row):
    """Crear reporte completo optimizado usando las utilidades centralizadas"""
    estilos = crear_estilos_excel()
    
    # Contenido específico según el tipo de reporte
    if tipo_reporte == 'movimientos':
        current_row = _agregar_seccion_movimientos(ws, resultado, current_row, estilos)
    elif tipo_reporte == 'inventario_articulos':
        current_row = _agregar_seccion_inventario_articulos(ws, resultado, current_row, estilos)
    elif tipo_reporte == 'inventario_instrumentos':
        current_row = _agregar_seccion_inventario_instrumentos(ws, resultado, current_row, estilos)
    elif tipo_reporte == 'proveedores':
        current_row = _agregar_seccion_proveedores(ws, resultado, current_row, estilos)
    elif tipo_reporte == 'consumos':
        current_row = _agregar_seccion_consumos(ws, resultado, current_row, estilos)
    
    return current_row

# Funciones auxiliares para Excel (mantenidas para compatibilidad)
def _aplicar_estilos_excel():
    """Definir estilos para Excel"""
    return {
        'header_font': Font(name='Calibri', size=12, bold=True, color="FFFFFF"),
        'header_fill': PatternFill(start_color="2E5984", end_color="2E5984", fill_type="solid"),
        'header_alignment': Alignment(horizontal="center", vertical="center"),
        'header_border': Border(left=Side(style='thin'), right=Side(style='thin'), top=Side(style='thin'), bottom=Side(style='thin')),
        'title_font': Font(name='Calibri', size=16, bold=True, color="2E5984"),
        'subtitle_font': Font(name='Calibri', size=14, bold=True, color="4472C4"),
        'title_alignment': Alignment(horizontal="center", vertical="center"),
        'data_font': Font(name='Calibri', size=10),
        'data_alignment': Alignment(horizontal="center", vertical="center"),
        'data_border': Border(left=Side(style='thin'), right=Side(style='thin'), top=Side(style='thin'), bottom=Side(style='thin'))
    }

def _crear_reporte_completo(workbook, tipo_reporte, periodo, fecha_inicio, fecha_fin, resultado):
    """Crear reporte completo en una sola hoja"""
    ws = workbook.active
    ws.title = f"Reporte {tipo_reporte.title()}"
    estilos = _aplicar_estilos_excel()
    
    current_row = 1
    
    # Encabezado principal
    ws[f'A{current_row}'] = "CONSERVATORIO NACIONAL DE MÚSICA"
    ws[f'A{current_row}'].font = estilos['title_font']
    ws[f'A{current_row}'].alignment = estilos['title_alignment']
    ws.merge_cells(f'A{current_row}:H{current_row}')
    current_row += 1
    
    ws[f'A{current_row}'] = "Sistema de Gestión de Inventario"
    ws[f'A{current_row}'].font = Font(name='Calibri', size=12, bold=True, color="4472C4")
    ws[f'A{current_row}'].alignment = Alignment(horizontal="center")
    ws.merge_cells(f'A{current_row}:H{current_row}')
    current_row += 3
    
    # Información del reporte
    ws[f'A{current_row}'] = "INFORMACIÓN DEL REPORTE"
    ws[f'A{current_row}'].font = estilos['subtitle_font']
    ws.merge_cells(f'A{current_row}:H{current_row}')
    current_row += 1
    
    info_data = [
        ["Tipo de Reporte:", tipo_reporte.replace('_', ' ').title()],
        ["Generado por:", current_user.username if current_user.is_authenticated else 'Sistema'],
        ["Fecha:", datetime.now().strftime('%d/%m/%Y %H:%M:%S')],
        ["Período:", periodo.replace('_', ' ').title() if periodo else 'N/A']
    ]
    
    for label, value in info_data:
        ws[f'A{current_row}'] = label
        ws[f'A{current_row}'].font = Font(bold=True)
        ws[f'B{current_row}'] = value
        current_row += 1
    
    current_row += 2
    
    # Contenido específico según el tipo de reporte
    if tipo_reporte == 'movimientos':
        current_row = _agregar_seccion_movimientos(ws, resultado, current_row, estilos)
    elif tipo_reporte == 'inventario_articulos':
        current_row = _agregar_seccion_inventario_articulos(ws, resultado, current_row, estilos)
    elif tipo_reporte == 'inventario_instrumentos':
        current_row = _agregar_seccion_inventario_instrumentos(ws, resultado, current_row, estilos)
    elif tipo_reporte == 'proveedores':
        current_row = _agregar_seccion_proveedores(ws, resultado, current_row, estilos)
    elif tipo_reporte == 'consumos':
        current_row = _agregar_seccion_consumos(ws, resultado, current_row, estilos)
    
    # Ajustar anchos de columnas
    for col in range(1, 9):
        ws.column_dimensions[chr(64 + col)].width = 15

def _agregar_seccion_movimientos(ws, resultado, start_row, estilos):
    """Agregar sección de movimientos"""
    current_row = start_row
    
    # Resumen si existe
    if resultado.get('resumen'):
        ws[f'A{current_row}'] = "RESUMEN DE MOVIMIENTOS"
        ws[f'A{current_row}'].font = estilos['subtitle_font']
        ws.merge_cells(f'A{current_row}:H{current_row}')
        current_row += 2
        
        # Encabezados del resumen
        headers_resumen = ['Tipo', 'Total Cantidad', 'Total Valor', 'Movimientos']
        for col, header in enumerate(headers_resumen, 1):
            cell = ws.cell(row=current_row, column=col, value=header)
            cell.font = estilos['header_font']
            cell.fill = estilos['header_fill']
            cell.alignment = estilos['header_alignment']
            cell.border = estilos['header_border']
        current_row += 1
        
        # Datos del resumen
        for item in resultado['resumen']:
            ws.cell(row=current_row, column=1, value=item.get('tipo_movimiento', ''))
            ws.cell(row=current_row, column=2, value=item.get('total_cantidad', 0))
            ws.cell(row=current_row, column=3, value=item.get('total_valor', 0))
            ws.cell(row=current_row, column=4, value=item.get('total_movimientos', 0))
            
            for col in range(1, 5):
                cell = ws.cell(row=current_row, column=col)
                cell.font = estilos['data_font']
                cell.border = estilos['data_border']
            current_row += 1
        
        current_row += 2
    
    # Detalles si existen
    if resultado.get('detalles'):
        ws[f'A{current_row}'] = "DETALLE DE MOVIMIENTOS"
        ws[f'A{current_row}'].font = estilos['subtitle_font']
        ws.merge_cells(f'A{current_row}:H{current_row}')
        current_row += 2
        
        # Encabezados del detalle
        headers_detalle = ['Fecha', 'Tipo', 'Código', 'Nombre', 'Cantidad', 'V. Unitario', 'V. Total', 'Observaciones']
        for col, header in enumerate(headers_detalle, 1):
            cell = ws.cell(row=current_row, column=col, value=header)
            cell.font = estilos['header_font']
            cell.fill = estilos['header_fill']
            cell.alignment = estilos['header_alignment']
            cell.border = estilos['header_border']
        current_row += 1
        
        # Datos del detalle
        for detalle in resultado['detalles']:
            ws.cell(row=current_row, column=1, value=detalle.get('fecha', ''))
            ws.cell(row=current_row, column=2, value=detalle.get('tipo', ''))
            ws.cell(row=current_row, column=3, value=detalle.get('codigo_item', ''))
            ws.cell(row=current_row, column=4, value=detalle.get('nombre_item', ''))
            ws.cell(row=current_row, column=5, value=detalle.get('cantidad', 0))
            ws.cell(row=current_row, column=6, value=detalle.get('valor_unitario', 0))
            ws.cell(row=current_row, column=7, value=detalle.get('valor_total', 0))
            ws.cell(row=current_row, column=8, value=detalle.get('observaciones', ''))
            
            for col in range(1, 9):
                cell = ws.cell(row=current_row, column=col)
                cell.font = estilos['data_font']
                cell.border = estilos['data_border']
            current_row += 1
    
    return current_row

def _agregar_seccion_inventario_articulos(ws, resultado, start_row, estilos):
    """Agregar sección de inventario de artículos"""
    current_row = start_row
    
    ws[f'A{current_row}'] = "INVENTARIO DE ARTÍCULOS"
    ws[f'A{current_row}'].font = estilos['subtitle_font']
    ws.merge_cells(f'A{current_row}:H{current_row}')
    current_row += 2
    
    # Encabezados
    headers = ['Código', 'Nombre', 'Cantidad', 'Stock Mín', 'Stock Máx', 'V. Unitario', 'V. Total', 'Estado']
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=current_row, column=col, value=header)
        cell.font = estilos['header_font']
        cell.fill = estilos['header_fill']
        cell.alignment = estilos['header_alignment']
        cell.border = estilos['header_border']
    current_row += 1
    
    # Datos
    for art in resultado.get('articulos', []):
        ws.cell(row=current_row, column=1, value=art.get('codigo', ''))
        ws.cell(row=current_row, column=2, value=art.get('nombre', ''))
        ws.cell(row=current_row, column=3, value=art.get('cantidad', 0))
        ws.cell(row=current_row, column=4, value=art.get('stock_min', 0))
        ws.cell(row=current_row, column=5, value=art.get('stock_max', 0))
        ws.cell(row=current_row, column=6, value=art.get('valor_unitario', 0))
        ws.cell(row=current_row, column=7, value=art.get('valor_total', 0))
        ws.cell(row=current_row, column=8, value=art.get('estado_stock', ''))
        
        for col in range(1, 9):
            cell = ws.cell(row=current_row, column=col)
            cell.font = estilos['data_font']
            cell.border = estilos['data_border']
        current_row += 1
    
    return current_row

def _agregar_seccion_inventario_instrumentos(ws, resultado, start_row, estilos):
    """Agregar sección de inventario de instrumentos"""
    current_row = start_row
    
    ws[f'A{current_row}'] = "INVENTARIO DE INSTRUMENTOS"
    ws[f'A{current_row}'].font = estilos['subtitle_font']
    ws.merge_cells(f'A{current_row}:G{current_row}')
    current_row += 2
    
    # Encabezados
    headers = ['Código', 'Nombre', 'Marca', 'Modelo', 'Serie', 'Estado', 'Valor']
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=current_row, column=col, value=header)
        cell.font = estilos['header_font']
        cell.fill = estilos['header_fill']
        cell.alignment = estilos['header_alignment']
        cell.border = estilos['header_border']
    current_row += 1
    
    # Datos
    for inst in resultado.get('instrumentos', []):
        ws.cell(row=current_row, column=1, value=inst.get('codigo', ''))
        ws.cell(row=current_row, column=2, value=inst.get('nombre', ''))
        ws.cell(row=current_row, column=3, value=inst.get('marca', ''))
        ws.cell(row=current_row, column=4, value=inst.get('modelo', ''))
        ws.cell(row=current_row, column=5, value=inst.get('serie', ''))
        ws.cell(row=current_row, column=6, value=inst.get('estado', ''))
        ws.cell(row=current_row, column=7, value=inst.get('valor_unitario', 0))
        
        for col in range(1, 8):
            cell = ws.cell(row=current_row, column=col)
            cell.font = estilos['data_font']
            cell.border = estilos['data_border']
        current_row += 1
    
    return current_row

def _agregar_seccion_proveedores(ws, resultado, start_row, estilos):
    """Agregar sección de proveedores"""
    current_row = start_row
    
    ws[f'A{current_row}'] = "REPORTE DE PROVEEDORES"
    ws[f'A{current_row}'].font = estilos['subtitle_font']
    ws.merge_cells(f'A{current_row}:F{current_row}')
    current_row += 2
    
    # Encabezados
    headers = ['Código', 'Razón Social', 'CI/RUC', 'Teléfono', 'Entradas', 'Total Compras']
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=current_row, column=col, value=header)
        cell.font = estilos['header_font']
        cell.fill = estilos['header_fill']
        cell.alignment = estilos['header_alignment']
        cell.border = estilos['header_border']
    current_row += 1
    
    # Datos
    for prov in resultado.get('datos', []):
        ws.cell(row=current_row, column=1, value=prov.get('codigo', ''))
        ws.cell(row=current_row, column=2, value=prov.get('razon_social', ''))
        ws.cell(row=current_row, column=3, value=prov.get('ci_ruc', ''))
        ws.cell(row=current_row, column=4, value=prov.get('telefono', ''))
        ws.cell(row=current_row, column=5, value=prov.get('total_entradas', 0))
        ws.cell(row=current_row, column=6, value=prov.get('total_compras', 0))
        
        for col in range(1, 7):
            cell = ws.cell(row=current_row, column=col)
            cell.font = estilos['data_font']
            cell.border = estilos['data_border']
        current_row += 1
    
    return current_row

def _agregar_seccion_consumos(ws, resultado, start_row, estilos):
    """Agregar sección de consumos"""
    current_row = start_row
    
    ws[f'A{current_row}'] = "REPORTE DE CONSUMOS"
    ws[f'A{current_row}'].font = estilos['subtitle_font']
    ws.merge_cells(f'A{current_row}:E{current_row}')
    current_row += 2
    
    # Encabezados
    headers = ['Código', 'Nombre', 'Consumos', 'Cantidad', 'Valor Total']
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=current_row, column=col, value=header)
        cell.font = estilos['header_font']
        cell.fill = estilos['header_fill']
        cell.alignment = estilos['header_alignment']
        cell.border = estilos['header_border']
    current_row += 1
    
    # Datos
    for cons in resultado.get('datos', []):
        ws.cell(row=current_row, column=1, value=cons.get('codigo', ''))
        ws.cell(row=current_row, column=2, value=cons.get('nombre', ''))
        ws.cell(row=current_row, column=3, value=cons.get('total_consumos', 0))
        ws.cell(row=current_row, column=4, value=cons.get('total_cantidad', 0))
        ws.cell(row=current_row, column=5, value=cons.get('total_valor', 0))
        
        for col in range(1, 6):
            cell = ws.cell(row=current_row, column=col)
            cell.font = estilos['data_font']
            cell.border = estilos['data_border']
        current_row += 1
    
    return current_row

@bp.route('/exportar/pdf', methods=['POST'])
@login_required
def exportar_pdf():
    """Exportar reporte a PDF con cabecera institucional estandarizada"""
    data = request.form.to_dict()
    tipo_reporte = data.get('tipo_reporte')
    periodo = data.get('periodo')
    fecha_inicio = data.get('fecha_inicio')
    fecha_fin = data.get('fecha_fin')
    articulo_id = data.get('articulo_id')
    tipo_item = data.get('tipo_item')
    
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
        
        # Crear archivo PDF
        output = io.BytesIO()
        doc = SimpleDocTemplate(output, pagesize=A4)
        elements = []
        
        # Crear cabecera institucional estandarizada
        elements.extend(crear_cabecera_pdf(f"Reporte de {tipo_reporte.replace('_', ' ').title()}"))
        
        # Crear estilos
        styles = crear_estilos_pdf()
        
        # Agregar contenido según el tipo de reporte
        if tipo_reporte == 'movimientos':
            if resultado.get('resumen'):
                elements.extend(_crear_tabla_resumen_pdf(resultado['resumen'], styles))
            if resultado.get('detalles'):
                elements.extend(_crear_tabla_detalles_pdf(resultado['detalles'], styles))
        elif tipo_reporte == 'inventario_articulos':
            elements.extend(_crear_tabla_inventario_articulos_pdf(resultado['articulos'], styles))
        elif tipo_reporte == 'inventario_instrumentos':
            elements.extend(_crear_tabla_inventario_instrumentos_pdf(resultado['instrumentos'], styles))
        elif tipo_reporte == 'proveedores':
            elements.extend(_crear_tabla_proveedores_pdf(resultado['datos'], styles))
        elif tipo_reporte == 'consumos':
            elements.extend(_crear_tabla_consumos_pdf(resultado['datos'], styles))
        
        # Construir PDF
        doc.build(elements)
        output.seek(0)
        
        # Crear respuesta
        response = make_response(output.getvalue())
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'attachment; filename=CNM_Reporte_{tipo_reporte.title()}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf'
        
        return response
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Funciones auxiliares para PDF (optimizadas con utilidades centralizadas)

def _crear_tabla_resumen_pdf(resumen, styles):
    """Crear tabla de resumen para PDF"""
    elements = []
    elements.append(Paragraph("RESUMEN DE MOVIMIENTOS", styles['TituloSeccion']))
    
    # Datos de la tabla
    data = [['Tipo', 'Total Cantidad', 'Total Valor', 'Movimientos']]
    for item in resumen:
        data.append([
            item.get('tipo_movimiento', ''),
            str(item.get('total_cantidad', 0)),
            f"${item.get('total_valor', 0):,.2f}",
            str(item.get('total_movimientos', 0))
        ])
    
    # Crear tabla con estilo estandarizado
    table = Table(data, colWidths=[1.5*inch, 1.5*inch, 1.5*inch, 1.5*inch])
    table = aplicar_estilo_tabla_pdf(table)
    
    elements.append(table)
    elements.append(Spacer(1, 20))
    return elements

def _crear_tabla_detalles_pdf(detalles, styles):
    """Crear tabla de detalles para PDF"""
    elements = []
    elements.append(Paragraph("DETALLE DE MOVIMIENTOS", styles['TituloSeccion']))
    
    # Datos de la tabla (limitamos a 20 registros para PDF)
    data = [['Fecha', 'Tipo', 'Código', 'Nombre', 'Cantidad', 'V. Total']]
    for detalle in detalles[:20]:  # Limitar registros
        data.append([
            detalle.get('fecha', ''),
            detalle.get('tipo', ''),
            detalle.get('codigo_item', ''),
            detalle.get('nombre_item', '')[:20] + '...' if len(detalle.get('nombre_item', '')) > 20 else detalle.get('nombre_item', ''),
            str(detalle.get('cantidad', 0)),
            f"${detalle.get('valor_total', 0):,.2f}"
        ])
    
    # Crear tabla con estilo estandarizado
    table = Table(data, colWidths=[1*inch, 1*inch, 1*inch, 2*inch, 1*inch, 1*inch])
    table = aplicar_estilo_tabla_pdf(table)
    
    elements.append(table)
    if len(detalles) > 20:
        elements.append(Paragraph(f"Mostrando 20 de {len(detalles)} registros", styles['Normal']))
    elements.append(Spacer(1, 20))
    return elements

def _crear_tabla_inventario_articulos_pdf(articulos, styles):
    """Crear tabla de inventario de artículos para PDF"""
    elements = []
    elements.append(Paragraph("INVENTARIO DE ARTÍCULOS", styles['TituloSeccion']))
    
    data = [['Código', 'Nombre', 'Cantidad', 'Stock Mín', 'V. Total', 'Estado']]
    for art in articulos:
        data.append([
            art.get('codigo', ''),
            art.get('nombre', '')[:15] + '...' if len(art.get('nombre', '')) > 15 else art.get('nombre', ''),
            str(art.get('cantidad', 0)),
            str(art.get('stock_min', 0)),
            f"${art.get('valor_total', 0):,.2f}",
            art.get('estado_stock', '')
        ])
    
    table = Table(data, colWidths=[1*inch, 2*inch, 1*inch, 1*inch, 1.5*inch, 1*inch])
    table = aplicar_estilo_tabla_pdf(table)
    
    elements.append(table)
    return elements

def _crear_tabla_inventario_instrumentos_pdf(instrumentos, styles):
    """Crear tabla de inventario de instrumentos para PDF"""
    elements = []
    elements.append(Paragraph("INVENTARIO DE INSTRUMENTOS", styles['TituloSeccion']))
    
    data = [['Código', 'Nombre', 'Marca', 'Estado', 'Valor']]
    for inst in instrumentos:
        data.append([
            inst.get('codigo', ''),
            inst.get('nombre', '')[:15] + '...' if len(inst.get('nombre', '')) > 15 else inst.get('nombre', ''),
            inst.get('marca', ''),
            inst.get('estado', ''),
            f"${inst.get('valor_unitario', 0):,.2f}"
        ])
    
    table = Table(data, colWidths=[1*inch, 2*inch, 1.5*inch, 1*inch, 1.5*inch])
    table = aplicar_estilo_tabla_pdf(table)
    
    elements.append(table)
    return elements

def _crear_tabla_proveedores_pdf(proveedores, styles):
    """Crear tabla de proveedores para PDF"""
    elements = []
    elements.append(Paragraph("REPORTE DE PROVEEDORES", styles['TituloSeccion']))
    
    data = [['Código', 'Razón Social', 'CI/RUC', 'Entradas', 'Total Compras']]
    for prov in proveedores:
        data.append([
            prov.get('codigo', ''),
            prov.get('razon_social', '')[:20] + '...' if len(prov.get('razon_social', '')) > 20 else prov.get('razon_social', ''),
            prov.get('ci_ruc', ''),
            str(prov.get('total_entradas', 0)),
            f"${prov.get('total_compras', 0):,.2f}"
        ])
    
    table = Table(data, colWidths=[1*inch, 2*inch, 1.5*inch, 1*inch, 1.5*inch])
    table = aplicar_estilo_tabla_pdf(table)
    
    elements.append(table)
    return elements

def _crear_tabla_consumos_pdf(consumos, styles):
    """Crear tabla de consumos para PDF"""
    elements = []
    elements.append(Paragraph("REPORTE DE CONSUMOS", styles['TituloSeccion']))
    
    data = [['Código', 'Nombre', 'Consumos', 'Cantidad', 'Valor Total']]
    for cons in consumos:
        data.append([
            cons.get('codigo', ''),
            cons.get('nombre', '')[:20] + '...' if len(cons.get('nombre', '')) > 20 else cons.get('nombre', ''),
            str(cons.get('total_consumos', 0)),
            str(cons.get('total_cantidad', 0)),
            f"${cons.get('total_valor', 0):,.2f}"
        ])
    
    table = Table(data, colWidths=[1*inch, 2*inch, 1*inch, 1*inch, 1.5*inch])
    table = aplicar_estilo_tabla_pdf(table)
    
    elements.append(table)
    return elements