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
    
    def get_by_id_with_item(self, articulo_id):
        """Obtiene un artículo por ID con su información de item"""
        return db.session.query(Articulo, Item).join(Item, Articulo.i_id == Item.id).filter(Articulo.i_id == articulo_id).first()

    def search_by_name_or_code(self, termino):
        """Busca artículos por nombre o código"""
        termino = f"%{termino}%"
        return db.session.query(Articulo, Item).join(Item, Articulo.i_id == Item.id).filter(
            db.or_(
                Item.i_nombre.ilike(termino),
                Item.i_codigo.ilike(termino)
            )
        ).all()

    def update_with_item(self, articulo_id, **kwargs):
        """Actualiza un artículo y su item"""
        try:
            resultado = self.get_by_id_with_item(articulo_id)
            if not resultado:
                raise ValueError("Artículo no encontrado")
            
            articulo, item = resultado
            
            # Separar datos de artículo e item
            item_data = {}
            articulo_data = {}
            
            for key, value in kwargs.items():
                if key.startswith('i_'):
                    item_data[key] = value
                elif key.startswith('a_'):
                    articulo_data[key] = value
                else:
                    # Mapear campos comunes
                    if key in ['nombre']:
                        item_data['i_nombre'] = value
                    elif key in ['codigo']:
                        item_data['i_codigo'] = value
                    elif key in ['cantidad']:
                        item_data['i_cantidad'] = value
                    elif key in ['valor_unitario']:
                        item_data['i_vUnitario'] = value
                        item_data['i_vTotal'] = value * item.i_cantidad
                    elif key in ['cuenta_contable']:
                        articulo_data['a_c_contable'] = value
                    elif key in ['stock_min']:
                        articulo_data['a_stockMin'] = value
                    elif key in ['stock_max']:
                        articulo_data['a_stockMax'] = value
            
            # Actualizar item
            for key, value in item_data.items():
                setattr(item, key, value)
            
            # Actualizar artículo
            for key, value in articulo_data.items():
                setattr(articulo, key, value)
            
            db.session.commit()
            return articulo, item
        except Exception as e:
            db.session.rollback()
            raise e

    def delete_with_item(self, articulo_id):
        """Elimina un artículo y su item"""
        try:
            resultado = self.get_by_id_with_item(articulo_id)
            if not resultado:
                return False
            
            articulo, item = resultado
            
            # Eliminar artículo primero (por la relación)
            db.session.delete(articulo)
            # Luego eliminar item
            db.session.delete(item)
            
            db.session.commit()
            return True
        except Exception as e:
            db.session.rollback()
            raise e

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