from .base import BaseRepository
from app.database.models import Instrumento

class InstrumentoRepository(BaseRepository):
    def __init__(self):
        super().__init__(Instrumento)
    
    def get_by_serial(self, serial):
        return Instrumento.query.filter_by(i_serie=serial).first()
    
    def get_by_status(self, status):
        return Instrumento.query.filter_by(i_estado=status).all()