from .base import BaseRepository
from app.database.models import Proveedor

class ProveedorRepository(BaseRepository):
    def __init__(self):
        super().__init__(Proveedor)
    
    def get_by_codigo(self, codigo):
        """Busca un proveedor por código"""
        return Proveedor.query.filter_by(p_codigo=codigo).first()
    
    def get_by_ci_ruc(self, ci_ruc):
        """Busca un proveedor por CI/RUC"""
        return Proveedor.query.filter_by(p_ci_ruc=ci_ruc).first()
    
    def search_by_name(self, termino):
        """Busca proveedores por nombre o código (búsqueda parcial)"""
        return Proveedor.query.filter(
            (Proveedor.p_razonsocial.ilike(f'%{termino}%')) |
            (Proveedor.p_codigo.ilike(f'%{termino}%'))
        ).all()
    
    def get_by_p_estado(self, proveedor_p_estado):
        """Obtiene un proveedor por su estado"""
        return Proveedor.query.filter(Proveedor.p_estado == proveedor_p_estado).first()  # Corregido aquí
    
    def get_by_id(self, proveedor_id):
        """Obtiene un proveedor por ID"""
        return Proveedor.query.get(proveedor_id)