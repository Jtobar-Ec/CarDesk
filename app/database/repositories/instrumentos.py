from .base import BaseRepository
from app.database.models import Instrumento, Item
from app.database import db

class InstrumentoRepository(BaseRepository):
    def __init__(self):
        super().__init__(Instrumento)
    
    def get_all_with_items(self):
        """Obtiene todos los instrumentos con su información de item"""
        return db.session.query(Instrumento, Item).join(Item, Instrumento.i_id == Item.id).all()
    
    def get_by_serial(self, serial):
        """Busca un instrumento por número de serie"""
        return Instrumento.query.filter_by(i_serie=serial).first()
    
    def get_by_status(self, status):
        """Obtiene instrumentos por estado"""
        return Instrumento.query.filter_by(i_estado=status).all()
    
    def get_with_item(self, instrumento_id):
        """Obtiene un instrumento con su información de item"""
        return db.session.query(Instrumento, Item).join(Item, Instrumento.i_id == Item.id).filter(Instrumento.i_id == instrumento_id).first()