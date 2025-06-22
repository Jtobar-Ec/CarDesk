from .base import BaseRepository
from .instrumentos import InstrumentoRepository
from .articulos import ArticuloRepository
from .movimientos import MovimientoRepository
from .proveedores import ProveedorRepository

__all__ = [
    'BaseRepository',
    'InstrumentoRepository', 
    'ArticuloRepository',
    'MovimientoRepository',
    'ProveedorRepository'
]