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
    
    def search_by_name(self, nombre):
        """Busca proveedores por nombre (búsqueda parcial)"""
        return Proveedor.query.filter(Proveedor.p_razonsocial.contains(nombre)).all()