from app.database.repositories.instrumentos import InstrumentoRepository
from app.database.repositories.movimientos import MovimientoRepository
from app.database.models import Item

class InstrumentoService:
    def __init__(self):
        self.repo = InstrumentoRepository()
        self.movimiento_repo = MovimientoRepository()

    def obtener_todos(self):
        """Obtiene todos los instrumentos"""
        return self.repo.get_all()

    def obtener_por_id(self, instrumento_id):
        """Obtiene un instrumento por ID"""
        return self.repo.get_by_id(instrumento_id)

    def obtener_por_serie(self, serie):
        """Obtiene un instrumento por número de serie"""
        return self.repo.get_by_serial(serie)

    def obtener_por_estado(self, estado):
        """Obtiene instrumentos por estado"""
        return self.repo.get_by_status(estado)

    def crear_instrumento(self, codigo, nombre, marca, modelo, serie, estado, valor_unitario=0):
        """Crea un nuevo instrumento"""
        # Primero crear el item
        item = Item(
            i_codigo=codigo,
            i_nombre=nombre,
            i_tipo='instrumento',
            i_cantidad=1,  # Los instrumentos son únicos
            i_vUnitario=valor_unitario,
            i_vTotal=valor_unitario
        )
        item.save()
        
        # Luego crear el instrumento
        instrumento = self.repo.create(
            i_id=item.id,
            i_marca=marca,
            i_modelo=modelo,
            i_serie=serie,
            i_estado=estado
        )
        
        return instrumento

    def actualizar_estado(self, instrumento_id, nuevo_estado):
        """Actualiza el estado de un instrumento"""
        return self.repo.update(instrumento_id, i_estado=nuevo_estado)

    def obtener_movimientos(self, instrumento_id):
        """Obtiene los movimientos de un instrumento"""
        return self.movimiento_repo.get_by_item(instrumento_id)