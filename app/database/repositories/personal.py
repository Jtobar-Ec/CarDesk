from .base import BaseRepository
from app.database.models import Persona

class PersonalRepository(BaseRepository):
    def __init__(self):
        super().__init__(Persona)
    
    def get_by_codigo(self, codigo):
        """Busca una persona por código"""
        return Persona.query.filter_by(pe_codigo=codigo).first()
    
    def get_by_ci(self, ci):
        """Busca una persona por CI"""
        return Persona.query.filter_by(pe_ci=ci).first()
    
    def get_by_estado(self, estado):
        """Obtiene personas por estado"""
        return Persona.query.filter_by(pe_estado=estado).all()
    
    def get_by_cargo(self, cargo):
        """Obtiene personas por cargo"""
        return Persona.query.filter_by(pe_cargo=cargo).all()
    
    def search_by_name(self, termino):
        """Busca personas por nombre, apellido, código o CI"""
        return Persona.query.filter(
            (Persona.pe_nombre.ilike(f'%{termino}%')) |
            (Persona.pe_apellido.ilike(f'%{termino}%')) |
            (Persona.pe_codigo.ilike(f'%{termino}%')) |
            (Persona.pe_ci.ilike(f'%{termino}%'))
        ).all()
    
    def get_activos(self):
        """Obtiene todas las personas activas"""
        return Persona.query.filter_by(pe_estado='Activo').all()