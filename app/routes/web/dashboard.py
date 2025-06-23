from flask import Blueprint, render_template
from flask_login import login_required
from app.services import InstrumentoService, ArticuloService, ProveedorService

bp = Blueprint('dashboard', __name__)

@bp.route('/')
@login_required
def index():
    """Dashboard principal del sistema"""
    instrumento_service = InstrumentoService()
    articulo_service = ArticuloService()
    proveedor_service = ProveedorService()
    
    # Estadísticas básicas
    total_instrumentos = len(instrumento_service.obtener_todos())
    total_articulos = len(articulo_service.obtener_todos())
    total_proveedores = len(proveedor_service.obtener_todos())
    articulos_stock_bajo = len(articulo_service.obtener_stock_bajo())
    
    estadisticas = {
        'total_instrumentos': total_instrumentos,
        'total_articulos': total_articulos,
        'total_proveedores': total_proveedores,
        'articulos_stock_bajo': articulos_stock_bajo
    }
    
    # Artículos con stock bajo para alertas
    alertas_stock = articulo_service.obtener_stock_bajo()
    
    return render_template('dashboard/index.html', 
                         estadisticas=estadisticas, 
                         alertas_stock=alertas_stock)