"""
Utilidades para exportación de reportes con cabeceras institucionales estandarizadas
"""
from datetime import datetime
from flask_login import current_user
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.platypus import Paragraph, Spacer, Table, TableStyle
from reportlab.lib.units import inch

def crear_cabecera_excel(ws, titulo_reporte, current_row=1):
    """
    Crea cabecera institucional estandarizada para Excel
    
    Args:
        ws: Worksheet de openpyxl
        titulo_reporte: Título específico del reporte
        current_row: Fila inicial (por defecto 1)
    
    Returns:
        int: Siguiente fila disponible después de la cabecera
    """
    # Estilos
    title_font = Font(name='Calibri', size=16, bold=True, color="2E5984")
    subtitle_font = Font(name='Calibri', size=12, bold=True, color="4472C4")
    info_font = Font(name='Calibri', size=10, bold=True)
    title_alignment = Alignment(horizontal="center", vertical="center")
    
    # Encabezado principal
    ws[f'A{current_row}'] = "CONSERVATORIO NACIONAL DE MÚSICA"
    ws[f'A{current_row}'].font = title_font
    ws[f'A{current_row}'].alignment = title_alignment
    ws.merge_cells(f'A{current_row}:H{current_row}')
    current_row += 1
    
    ws[f'A{current_row}'] = "Sistema de Gestión de Inventario"
    ws[f'A{current_row}'].font = subtitle_font
    ws[f'A{current_row}'].alignment = title_alignment
    ws.merge_cells(f'A{current_row}:H{current_row}')
    current_row += 1
    
    ws[f'A{current_row}'] = "Cochapata E12-56, Quito - Ecuador"
    ws[f'A{current_row}'].font = Font(name='Calibri', size=10, color="4472C4")
    ws[f'A{current_row}'].alignment = title_alignment
    ws.merge_cells(f'A{current_row}:H{current_row}')
    current_row += 3
    
    # Información del reporte
    ws[f'A{current_row}'] = "INFORMACIÓN DEL REPORTE"
    ws[f'A{current_row}'].font = subtitle_font
    ws.merge_cells(f'A{current_row}:H{current_row}')
    current_row += 1
    
    info_data = [
        ["Tipo de Reporte:", titulo_reporte],
        ["Generado por:", current_user.username if current_user.is_authenticated else 'Sistema'],
        ["Fecha:", datetime.now().strftime('%d/%m/%Y %H:%M:%S')]
    ]
    
    for label, value in info_data:
        ws[f'A{current_row}'] = label
        ws[f'A{current_row}'].font = info_font
        ws[f'B{current_row}'] = value
        current_row += 1
    
    current_row += 2
    return current_row

def crear_estilos_excel():
    """Crear estilos estandarizados para Excel"""
    return {
        'header_font': Font(name='Calibri', size=12, bold=True, color="FFFFFF"),
        'header_fill': PatternFill(start_color="2E5984", end_color="2E5984", fill_type="solid"),
        'header_alignment': Alignment(horizontal="center", vertical="center"),
        'header_border': Border(left=Side(style='thin'), right=Side(style='thin'), 
                               top=Side(style='thin'), bottom=Side(style='thin')),
        'data_font': Font(name='Calibri', size=10),
        'data_alignment': Alignment(horizontal="center", vertical="center"),
        'data_border': Border(left=Side(style='thin'), right=Side(style='thin'), 
                             top=Side(style='thin'), bottom=Side(style='thin'))
    }

def crear_cabecera_pdf(titulo_reporte):
    """
    Crea cabecera institucional estandarizada para PDF
    
    Args:
        titulo_reporte: Título específico del reporte
    
    Returns:
        list: Lista de elementos para agregar al PDF
    """
    elements = []
    styles = getSampleStyleSheet()
    
    # Estilos personalizados
    title_style = ParagraphStyle(
        'TituloInstitucional',
        parent=styles['Title'],
        fontSize=18,
        fontName='Helvetica-Bold',
        textColor=colors.HexColor('#2E5984'),
        alignment=1,
        spaceAfter=10
    )
    
    subtitle_style = ParagraphStyle(
        'SubtituloInstitucional',
        parent=styles['Normal'],
        fontSize=12,
        fontName='Helvetica',
        textColor=colors.HexColor('#4472C4'),
        alignment=1,
        spaceAfter=20
    )
    
    # Encabezado institucional
    elements.append(Paragraph("CONSERVATORIO NACIONAL DE MÚSICA", title_style))
    elements.append(Paragraph("Sistema de Gestión de Inventario", subtitle_style))
    elements.append(Paragraph("Cochapata E12-56, Quito - Ecuador", subtitle_style))
    elements.append(Spacer(1, 20))
    
    # Información del reporte
    info_style = ParagraphStyle(
        'TituloSeccion',
        parent=styles['Heading2'],
        fontSize=14,
        fontName='Helvetica-Bold',
        textColor=colors.HexColor('#2E5984'),
        spaceBefore=20,
        spaceAfter=12
    )
    
    elements.append(Paragraph("INFORMACIÓN DEL REPORTE", info_style))
    
    # Tabla de información
    info_data = [
        ['Tipo de Reporte:', titulo_reporte],
        ['Generado por:', current_user.username if current_user.is_authenticated else 'Sistema'],
        ['Fecha de Generación:', datetime.now().strftime('%d/%m/%Y %H:%M:%S')]
    ]
    
    info_table = Table(info_data, colWidths=[2*inch, 3*inch])
    info_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#F8F9FA'))
    ]))
    
    elements.append(info_table)
    elements.append(Spacer(1, 20))
    
    return elements

def crear_estilos_pdf():
    """Crear estilos estandarizados para PDF"""
    styles = getSampleStyleSheet()
    
    # Estilo para títulos de sección
    styles.add(ParagraphStyle(
        name='TituloSeccion',
        parent=styles['Heading2'],
        fontSize=14,
        fontName='Helvetica-Bold',
        textColor=colors.HexColor('#2E5984'),
        spaceBefore=20,
        spaceAfter=12
    ))
    
    return styles

def aplicar_estilo_tabla_pdf(table):
    """Aplicar estilo estandarizado a tablas PDF"""
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2E5984')),
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
    return table

def ajustar_columnas_excel(ws):
    """Ajustar automáticamente el ancho de columnas en Excel"""
    from openpyxl.cell.cell import MergedCell
    
    for column in ws.columns:
        max_length = 0
        column_letter = None
        
        for cell in column:
            # Saltar celdas combinadas
            if isinstance(cell, MergedCell):
                continue
                
            # Obtener la letra de la columna de la primera celda válida
            if column_letter is None:
                column_letter = cell.column_letter
            
            try:
                if cell.value and len(str(cell.value)) > max_length:
                    max_length = len(str(cell.value))
            except Exception:
                pass
        
        # Solo ajustar si encontramos una columna válida
        if column_letter:
            adjusted_width = min(max_length + 2, 50) if max_length > 0 else 15
            ws.column_dimensions[column_letter].width = adjusted_width