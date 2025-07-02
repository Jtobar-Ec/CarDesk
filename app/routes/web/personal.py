from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, make_response
from flask_login import login_required
from app.services.personal_service import PersonalService
from datetime import date, datetime
from sqlalchemy import or_, and_
from app.database.models import Persona
from app.database import db
import io
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from app.utils.export_utils import (
    crear_cabecera_excel, crear_estilos_excel, crear_cabecera_pdf,
    crear_estilos_pdf, aplicar_estilo_tabla_pdf, ajustar_columnas_excel
)

bp = Blueprint('personal', __name__)
personal_service = PersonalService()

@bp.route('/')
@login_required
def listar_personal():
    """Lista todo el personal con filtros, paginación y exportación"""
    # Parámetros de filtrado
    buscar = request.args.get('buscar', '').strip()
    cargo = request.args.get('cargo', '')
    estado = request.args.get('estado', '')
    ordenar = request.args.get('ordenar', 'nombre')
    
    # Parámetros de paginación
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    # Verificar si es exportación
    export_type = request.args.get('export')
    if export_type in ['excel', 'pdf']:
        # Para exportación, obtener todos los registros sin paginación
        query = Persona.query
        
        # Aplicar filtros
        if buscar:
            query = query.filter(
                or_(
                    Persona.pe_nombre.ilike(f'%{buscar}%'),
                    Persona.pe_codigo.ilike(f'%{buscar}%'),
                    Persona.pe_ci.ilike(f'%{buscar}%'),
                    Persona.pe_correo.ilike(f'%{buscar}%')
                )
            )
        
        if cargo:
            query = query.filter(Persona.pe_cargo == cargo)
            
        if estado:
            query = query.filter(Persona.pe_estado == estado)
        
        # Aplicar ordenamiento
        if ordenar == 'nombre':
            query = query.order_by(Persona.pe_nombre.asc())
        elif ordenar == 'codigo':
            query = query.order_by(Persona.pe_codigo.asc())
        elif ordenar == 'cargo':
            query = query.order_by(Persona.pe_cargo.asc())
        elif ordenar == 'estado':
            query = query.order_by(Persona.pe_estado.asc())
        
        personal_export = query.all()
        
        if export_type == 'excel':
            return _exportar_personal_excel(personal_export)
        elif export_type == 'pdf':
            return _exportar_personal_pdf(personal_export)
    
    # Consulta base
    query = Persona.query
    
    # Aplicar filtros
    if buscar:
        query = query.filter(
            or_(
                Persona.pe_nombre.ilike(f'%{buscar}%'),
                Persona.pe_codigo.ilike(f'%{buscar}%'),
                Persona.pe_ci.ilike(f'%{buscar}%'),
                Persona.pe_correo.ilike(f'%{buscar}%')
            )
        )
    
    if cargo:
        query = query.filter(Persona.pe_cargo == cargo)
        
    if estado:
        query = query.filter(Persona.pe_estado == estado)
    
    # Aplicar ordenamiento
    if ordenar == 'nombre':
        query = query.order_by(Persona.pe_nombre.asc())
    elif ordenar == 'codigo':
        query = query.order_by(Persona.pe_codigo.asc())
    elif ordenar == 'cargo':
        query = query.order_by(Persona.pe_cargo.asc())
    elif ordenar == 'estado':
        query = query.order_by(Persona.pe_estado.asc())
    
    # Aplicar paginación
    pagination = query.paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    # Obtener opciones para filtros
    cargos_disponibles = db.session.query(Persona.pe_cargo).distinct().filter(Persona.pe_cargo.isnot(None)).all()
    cargos_disponibles = [cargo[0] for cargo in cargos_disponibles if cargo[0]]
    
    return render_template('personal/list.html',
                         personal=pagination.items,
                         pagination=pagination,
                         cargos_disponibles=cargos_disponibles)

@bp.route('/nuevo', methods=['GET', 'POST'])
@login_required
def nuevo_personal():
    """Crear una nueva persona"""
    if request.method == 'POST':
        try:
            nombre = request.form['nombre']
            apellido = request.form['apellido']
            ci = request.form['ci']
            telefono = request.form.get('telefono')
            correo = request.form.get('correo')
            direccion = request.form.get('direccion')
            cargo = request.form.get('cargo')
            estado = request.form.get('estado', 'Activo')
            
            personal_service.crear_persona(
                nombre=nombre,
                apellido=apellido,
                ci=ci,
                telefono=telefono,
                correo=correo,
                direccion=direccion,
                cargo=cargo,
                estado=estado
            )
            
            flash('Persona creada exitosamente', 'success')
            return redirect(url_for('personal.listar_personal'))
        except Exception as e:
            flash(f'Error al crear persona: {str(e)}', 'error')
    
    # Obtener opciones para los selects
    cargos = personal_service.obtener_cargos_disponibles()
    estados = personal_service.obtener_estados_disponibles()
    return render_template('personal/form.html', cargos=cargos, estados=estados)

@bp.route('/<int:persona_id>')
@login_required
def detalle_personal(persona_id):
    """Ver detalles de una persona"""
    persona = personal_service.obtener_por_id(persona_id)
    if not persona:
        flash('Persona no encontrada', 'error')
        return redirect(url_for('personal.listar_personal'))
    
    # Obtener historial de consumos
    consumos = personal_service.obtener_historial_consumos(persona_id)
    
    # Verificar si es exportación
    export_type = request.args.get('export')
    if export_type in ['excel', 'pdf']:
        if export_type == 'excel':
            return _exportar_detalle_personal_excel(persona, consumos)
        elif export_type == 'pdf':
            return _exportar_detalle_personal_pdf(persona, consumos)
    
    today = date.today().strftime('%Y-%m-%d')
    return render_template('personal/detail.html', persona=persona, consumos=consumos, today=today)

@bp.route('/<int:persona_id>/editar', methods=['GET', 'POST'])
@login_required
def editar_personal(persona_id):
    """Editar una persona"""
    persona = personal_service.obtener_por_id(persona_id)
    if not persona:
        flash('Persona no encontrada', 'error')
        return redirect(url_for('personal.listar_personal'))
    
    if request.method == 'POST':
        try:
            # Obtener todos los campos del formulario
            datos = {
                'nombre': request.form['nombre'],
                'apellido': request.form.get('apellido', ''),
                'ci': request.form.get('ci', ''),
                'telefono': request.form.get('telefono', ''),
                'correo': request.form.get('correo', ''),
                'direccion': request.form.get('direccion', ''),
                'cargo': request.form.get('cargo', ''),
                'estado': request.form.get('estado', 'Activo')
            }
            
            personal_service.actualizar_persona(persona_id, **datos)
            flash('Persona actualizada exitosamente', 'success')
            return redirect(url_for('personal.detalle_personal', persona_id=persona_id))
        except Exception as e:
            flash(f'Error al actualizar persona: {str(e)}', 'error')
    
    # Obtener opciones para los selects
    cargos = personal_service.obtener_cargos_disponibles()
    estados = personal_service.obtener_estados_disponibles()
    return render_template('personal/form.html', persona=persona, cargos=cargos, estados=estados)

@bp.route('/<int:persona_id>/eliminar', methods=['POST'])
@login_required
def eliminar_personal(persona_id):
    """Eliminar una persona"""
    try:
        if personal_service.eliminar_persona(persona_id):
            flash('Persona eliminada exitosamente', 'success')
        else:
            flash('No se pudo eliminar la persona', 'error')
    except Exception as e:
        flash(f'Error al eliminar persona: {str(e)}', 'error')
    
    return redirect(url_for('personal.listar_personal'))

@bp.route('/<int:persona_id>/cambiar-estado', methods=['POST'])
@login_required
def cambiar_estado(persona_id):
    """Cambiar el estado de una persona"""
    try:
        nuevo_estado = request.form['estado']
        personal_service.cambiar_estado(persona_id, nuevo_estado)
        flash(f'Estado cambiado a {nuevo_estado} exitosamente', 'success')
    except Exception as e:
        flash(f'Error al cambiar estado: {str(e)}', 'error')
    
    return redirect(request.referrer or url_for('personal.listar_personal'))

@bp.route('/buscar')
@login_required
def buscar_personal():
    """Buscar personal por nombre, apellido o código"""
    termino = request.args.get('termino', '').strip()
    personal = []
    
    # Solo buscar si hay un término de búsqueda válido
    if termino and len(termino) >= 2:
        personal = personal_service.buscar_por_nombre(termino)
    elif termino and len(termino) < 2:
        # Si el término es muy corto, mostrar mensaje de error
        flash('El término de búsqueda debe tener al menos 2 caracteres', 'warning')
    
    return render_template('personal/search.html', personal=personal, termino=termino)

@bp.route('/activos')
@login_required
def personal_activo():
    """Lista solo el personal activo"""
    personal = personal_service.obtener_activos()
    return render_template('personal/list.html', personal=personal, titulo="Personal Activo")

@bp.route('/por-cargo/<cargo>')
@login_required
def personal_por_cargo(cargo):
    """Lista personal por cargo"""
    personal = personal_service.obtener_por_cargo(cargo)
    return render_template('personal/list.html', personal=personal, titulo=f"Personal - {cargo}")

@bp.route('/api/activos')
@login_required
def api_personal_activo():
    """API endpoint para obtener personal activo en formato JSON"""
    try:
        personal = personal_service.obtener_activos()
        personal_data = []
        
        for persona in personal:
            personal_data.append({
                'id': persona.id,
                'nombre': persona.pe_nombre,
                'apellido': persona.pe_apellido or '',
                'ci': persona.pe_ci or '',
                'telefono': persona.pe_telefono or '',
                'correo': persona.pe_correo or '',
                'direccion': persona.pe_direccion or '',
                'cargo': persona.pe_cargo or '',
                'estado': persona.pe_estado
            })
        
        return jsonify({
            'success': True,
            'personal': personal_data,
            'total': len(personal_data)
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'personal': []
        }), 500

def _exportar_personal_excel(personal):
    """Exporta personal a Excel con cabecera institucional"""
    wb = Workbook()
    ws = wb.active
    ws.title = "Personal"
    
    # Configurar orientación horizontal
    ws.page_setup.orientation = ws.ORIENTATION_LANDSCAPE
    
    # Crear cabecera institucional
    current_row = crear_cabecera_excel(ws, "Reporte de Personal")
    
    # Obtener estilos
    estilos = crear_estilos_excel()
    
    # Encabezados de datos
    headers = ['Código', 'Nombre', 'CI', 'Teléfono', 'Correo', 'Dirección', 'Cargo', 'Estado']
    
    # Escribir encabezados
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=current_row, column=col, value=header)
        cell.font = estilos['header_font']
        cell.fill = estilos['header_fill']
        cell.alignment = estilos['header_alignment']
        cell.border = estilos['header_border']
    current_row += 1
    
    # Escribir datos
    for persona in personal:
        ws.cell(row=current_row, column=1, value=persona.pe_codigo or '')
        ws.cell(row=current_row, column=2, value=persona.pe_nombre or '')
        ws.cell(row=current_row, column=3, value=persona.pe_ci or '')
        ws.cell(row=current_row, column=4, value=persona.pe_telefono or '')
        ws.cell(row=current_row, column=5, value=persona.pe_correo or '')
        ws.cell(row=current_row, column=6, value=persona.pe_direccion or '')
        ws.cell(row=current_row, column=7, value=persona.pe_cargo or '')
        ws.cell(row=current_row, column=8, value=persona.pe_estado or '')
        
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
    response.headers['Content-Disposition'] = f'attachment; filename=CNM_Personal_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
    
    return response

def _exportar_personal_pdf(personal):
    """Exporta personal a PDF con cabecera institucional"""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4),
                          rightMargin=0.5*inch, leftMargin=0.5*inch,
                          topMargin=0.5*inch, bottomMargin=0.5*inch)
    
    elements = []
    
    # Crear cabecera institucional
    elements.extend(crear_cabecera_pdf("Reporte de Personal"))
    
    # Obtener estilos
    styles = crear_estilos_pdf()
    
    # Título de la sección de datos
    elements.append(Paragraph("LISTADO DE PERSONAL", styles['TituloSeccion']))
    elements.append(Paragraph(f"Total de registros: {len(personal)}", styles['Normal']))
    elements.append(Spacer(1, 12))
    
    # Datos de la tabla
    data = [['Código', 'Nombre', 'CI', 'Teléfono', 'Correo', 'Cargo', 'Estado']]
    
    for persona in personal:
        data.append([
            persona.pe_codigo or '',
            (persona.pe_nombre or '')[:25] + '...' if persona.pe_nombre and len(persona.pe_nombre) > 25 else (persona.pe_nombre or ''),
            persona.pe_ci or '',
            persona.pe_telefono or '',
            (persona.pe_correo or '')[:20] + '...' if persona.pe_correo and len(persona.pe_correo) > 20 else (persona.pe_correo or ''),
            persona.pe_cargo or '',
            persona.pe_estado or ''
        ])
    
    # Crear tabla
    table = Table(data, colWidths=[0.8*inch, 2.0*inch, 0.8*inch, 1.0*inch, 1.5*inch, 1.0*inch, 0.8*inch])
    
    # Aplicar estilo estandarizado
    aplicar_estilo_tabla_pdf(table)
    
    elements.append(table)
    
    # Construir PDF
    doc.build(elements)
    buffer.seek(0)
    
    response = make_response(buffer.read())
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename=CNM_Personal_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf'
    
    return response

def _exportar_detalle_personal_excel(persona, consumos):
    """Exporta detalle de personal a Excel con cabecera institucional"""
    wb = Workbook()
    ws = wb.active
    ws.title = f"Detalle_{persona.pe_nombre}"
    
    # Configurar orientación horizontal
    ws.page_setup.orientation = ws.ORIENTATION_LANDSCAPE
    
    # Crear cabecera institucional
    current_row = crear_cabecera_excel(ws, f"Detalle de Personal - {persona.pe_nombre}")
    
    # Obtener estilos
    estilos = crear_estilos_excel()
    
    # Información personal
    info_headers = ['Campo', 'Valor']
    for col, header in enumerate(info_headers, 1):
        cell = ws.cell(row=current_row, column=col, value=header)
        cell.font = estilos['header_font']
        cell.fill = estilos['header_fill']
        cell.alignment = estilos['header_alignment']
        cell.border = estilos['header_border']
    current_row += 1
    
    # Datos personales
    info_data = [
        ['Código', persona.pe_codigo or ''],
        ['Nombre', persona.pe_nombre or ''],
        ['CI', persona.pe_ci or ''],
        ['Teléfono', persona.pe_telefono or ''],
        ['Correo', persona.pe_correo or ''],
        ['Dirección', persona.pe_direccion or ''],
        ['Cargo', persona.pe_cargo or ''],
        ['Estado', persona.pe_estado or '']
    ]
    
    for campo, valor in info_data:
        ws.cell(row=current_row, column=1, value=campo).font = estilos['data_font']
        ws.cell(row=current_row, column=2, value=valor).font = estilos['data_font']
        current_row += 1
    
    current_row += 2  # Espacio antes de asignaciones
    
    # Historial de asignaciones
    if consumos:
        ws.cell(row=current_row, column=1, value="HISTORIAL DE ASIGNACIONES").font = estilos['header_font']
        current_row += 2
        
        # Encabezados de asignaciones
        headers = ['Fecha', 'Artículo', 'Cantidad', 'Estado', 'Observaciones']
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=current_row, column=col, value=header)
            cell.font = estilos['header_font']
            cell.fill = estilos['header_fill']
            cell.alignment = estilos['header_alignment']
            cell.border = estilos['header_border']
        current_row += 1
        
        # Datos de asignaciones
        for consumo in consumos:
            ws.cell(row=current_row, column=1, value=consumo.c_fecha.strftime('%d/%m/%Y') if consumo.c_fecha else '')
            ws.cell(row=current_row, column=2, value=consumo.item.i_nombre if consumo.item else '')
            ws.cell(row=current_row, column=3, value=consumo.c_cantidad or 0)
            ws.cell(row=current_row, column=4, value=consumo.c_estado or '')
            ws.cell(row=current_row, column=5, value=consumo.c_observaciones or '')
            
            # Aplicar estilos a los datos
            for col in range(1, 6):
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
    response.headers['Content-Disposition'] = f'attachment; filename=CNM_Detalle_{persona.pe_nombre}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
    
    return response

def _exportar_detalle_personal_pdf(persona, consumos):
    """Exporta detalle de personal a PDF con cabecera institucional"""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4,
                          rightMargin=0.5*inch, leftMargin=0.5*inch,
                          topMargin=0.5*inch, bottomMargin=0.5*inch)
    
    elements = []
    
    # Crear cabecera institucional
    elements.extend(crear_cabecera_pdf(f"Detalle de Personal - {persona.pe_nombre}"))
    
    # Obtener estilos
    styles = crear_estilos_pdf()
    
    # Título de la sección de información
    elements.append(Paragraph("INFORMACIÓN PERSONAL", styles['TituloSeccion']))
    elements.append(Spacer(1, 12))
    
    # Información personal
    info_data = [
        ['Código:', persona.pe_codigo or '-'],
        ['Nombre:', persona.pe_nombre or '-'],
        ['CI:', persona.pe_ci or '-'],
        ['Teléfono:', persona.pe_telefono or '-'],
        ['Correo:', persona.pe_correo or '-'],
        ['Dirección:', persona.pe_direccion or '-'],
        ['Cargo:', persona.pe_cargo or '-'],
        ['Estado:', persona.pe_estado or '-']
    ]
    
    info_table = Table(info_data, colWidths=[1.5*inch, 4*inch])
    info_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
    ]))
    
    elements.append(info_table)
    elements.append(Spacer(1, 20))
    
    # Historial de asignaciones
    if consumos:
        elements.append(Paragraph("HISTORIAL DE ASIGNACIONES", styles['TituloSeccion']))
        elements.append(Paragraph(f"Total de asignaciones: {len(consumos)}", styles['Normal']))
        elements.append(Spacer(1, 12))
        
        consumos_data = [['Fecha', 'Artículo', 'Cantidad', 'Estado', 'Observaciones']]
        for consumo in consumos:
            consumos_data.append([
                consumo.c_fecha.strftime('%d/%m/%Y') if consumo.c_fecha else '-',
                (consumo.item.i_nombre if consumo.item else '-')[:30] + '...' if consumo.item and len(consumo.item.i_nombre) > 30 else (consumo.item.i_nombre if consumo.item else '-'),
                str(consumo.c_cantidad or 0),
                consumo.c_estado or '-',
                (consumo.c_observaciones or '-')[:20] + '...' if consumo.c_observaciones and len(consumo.c_observaciones) > 20 else (consumo.c_observaciones or '-')
            ])
        
        consumos_table = Table(consumos_data, colWidths=[1*inch, 2*inch, 0.8*inch, 1*inch, 1.5*inch])
        
        # Aplicar estilo estandarizado
        aplicar_estilo_tabla_pdf(consumos_table)
        
        elements.append(consumos_table)
    
    # Construir PDF
    doc.build(elements)
    buffer.seek(0)
    
    response = make_response(buffer.read())
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename=CNM_Detalle_{persona.pe_nombre}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf'
    
    return response