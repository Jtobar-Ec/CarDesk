from .base import BaseRepository
from app.database.models import Articulo, Item
from app.database import db

class ArticuloRepository(BaseRepository):
    def __init__(self):
        super().__init__(Articulo)
    
    def get_all_with_items(self):
        """Obtiene todos los artículos con su información de item"""
        return db.session.query(Articulo, Item).join(Item, Articulo.i_id == Item.id).all()
    
    def get_by_codigo(self, codigo):
        """Busca un artículo por código del item"""
        return db.session.query(Articulo, Item).join(Item, Articulo.i_id == Item.id).filter(Item.i_codigo == codigo).first()
    
    def get_low_stock(self):
        """Obtiene artículos con stock bajo (menor al mínimo)"""
        return db.session.query(Articulo, Item).join(Item, Articulo.i_id == Item.id).filter(Item.i_cantidad <= Articulo.a_stockMin).all()
    
    def create_with_item(self, item_data, articulo_data):
        """Crea un artículo junto con su item"""
        try:
            # Crear el item primero
            item = Item(**item_data)
            db.session.add(item)
            db.session.flush()  # Para obtener el ID
            
            # Crear el artículo
            articulo_data['i_id'] = item.id
            articulo = Articulo(**articulo_data)
            db.session.add(articulo)
            
            db.session.commit()
            return articulo, item
        except Exception as e:
            db.session.rollback()
            raise e