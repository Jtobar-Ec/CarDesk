from app.database.repositories.articulos import ArticuloRepository
from app.database.repositories.movimientos import MovimientoRepository

class ArticuloService:
    def __init__(self):
        self.repo = ArticuloRepository()
        self.movimiento_repo = MovimientoRepository()

    def obtener_todos(self):
        """Obtiene todos los artículos con su información de item"""
        return self.repo.get_all_with_items()

    def obtener_por_codigo(self, codigo):
        """Obtiene un artículo por código"""
        return self.repo.get_by_codigo(codigo)

    def obtener_stock_bajo(self):
        """Obtiene artículos con stock bajo"""
        return self.repo.get_low_stock()

    def crear_articulo(self, codigo, nombre, cantidad, valor_unitario, cuenta_contable, stock_min=0, stock_max=100):
        """Crea un nuevo artículo"""
        item_data = {
            'i_codigo': codigo,
            'i_nombre': nombre,
            'i_tipo': 'articulo',
            'i_cantidad': cantidad,
            'i_vUnitario': valor_unitario,
            'i_vTotal': cantidad * valor_unitario
        }
        
        articulo_data = {
            'a_c_contable': cuenta_contable,
            'a_stockMin': stock_min,
            'a_stockMax': stock_max
        }
        
        return self.repo.create_with_item(item_data, articulo_data)

    def obtener_movimientos(self, articulo_id):
        """Obtiene los movimientos de un artículo"""
        return self.movimiento_repo.get_by_item(articulo_id)

    def registrar_entrada(self, articulo_id, cantidad, valor_unitario, usuario_id, observaciones=None):
        """Registra una entrada de artículo"""
        return self.movimiento_repo.crear_entrada(
            articulo_id, cantidad, valor_unitario, usuario_id, observaciones=observaciones
        )

    def registrar_salida(self, articulo_id, cantidad, valor_unitario, usuario_id, observaciones=None):
        """Registra una salida de artículo"""
        return self.movimiento_repo.crear_salida(
            articulo_id, cantidad, valor_unitario, usuario_id, observaciones=observaciones
        )