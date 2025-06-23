from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required
from datetime import datetime, date
from sqlalchemy import func, extract, and_
from app.database.models import (
    MovimientoDetalle, Item, Articulo, Instrumento, 
    Proveedor, Persona, Consumo, Entrada
)
from app.database import db

bp = Blueprint('reportes', __name__)

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
    
    try:
        if tipo_reporte == 'movimientos':
            resultado = _generar_reporte_movimientos(periodo, fecha_inicio, fecha_fin, articulo_id)
        elif tipo_reporte == 'inventario':
            resultado = _generar_reporte_inventario()
        elif tipo_reporte == 'proveedores':
            resultado = _generar_reporte_proveedores(periodo, fecha_inicio, fecha_fin)
        elif tipo_reporte == 'consumos':
            resultado = _generar_reporte_consumos(periodo, fecha_inicio, fecha_fin)
        else:
            return jsonify({'error': 'Tipo de reporte no válido'}), 400
            
        return jsonify(resultado)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def _generar_reporte_movimientos(periodo, fecha_inicio, fecha_fin, articulo_id=None):
    """Generar reporte de movimientos (ingresos/egresos)"""
    query = db.session.query(
        MovimientoDetalle.m_tipo,
        func.sum(MovimientoDetalle.m_cantidad).label('total_cantidad'),
        func.sum(MovimientoDetalle.m_valorTotal).label('total_valor'),
        func.count(MovimientoDetalle.id).label('total_movimientos')
    )
    
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
                'tipo_movimiento': mov.m_tipo,
                'total_cantidad': int(mov.total_cantidad),
                'total_valor': float(mov.total_valor),
                'total_movimientos': mov.total_movimientos
            } for mov in movimientos
        ],
        'detalles': [
            {
                'fecha': mov.m_fecha.strftime('%Y-%m-%d'),
                'tipo': mov.m_tipo,
                'codigo_item': codigo,
                'nombre_item': nombre,
                'cantidad': mov.m_cantidad,
                'valor_unitario': float(mov.m_valorUnitario),
                'valor_total': float(mov.m_valorTotal),
                'proveedor': proveedor or 'N/A',
                'persona': persona or 'N/A',
                'observaciones': mov.m_observaciones or ''
            } for mov, codigo, nombre, proveedor, persona in detalles
        ]
    }

def _generar_reporte_inventario():
    """Generar reporte de inventario actual"""
    # Artículos
    articulos = db.session.query(
        Item, Articulo
    ).join(Articulo, Item.id == Articulo.i_id)\
     .filter(Item.i_tipo == 'articulo').all()
    
    # Instrumentos
    instrumentos = db.session.query(
        Item, Instrumento
    ).join(Instrumento, Item.id == Instrumento.i_id)\
     .filter(Item.i_tipo == 'instrumento').all()
    
    return {
        'tipo': 'inventario',
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
        ],
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
    articulos = db.session.query(Item).filter(Item.i_tipo == 'articulo').all()
    return jsonify([
        {
            'id': art.id,
            'codigo': art.i_codigo,
            'nombre': art.i_nombre
        } for art in articulos
    ])