from app.database.repositories.articulos import ArticuloRepository
from app.database.repositories.movimientos import MovimientoRepository

class ArticuloService:
    def __init__(self):
        self.repo = ArticuloRepository()
        self.movimiento_repo = MovimientoRepository()

    def obtener_todos_articulos(self):
        """Obtiene todos los artículos con su información de item"""
        return self.repo.get_all_with_items()

    def obtener_todos(self):
        """Alias para compatibilidad"""
        return self.obtener_todos_articulos()

    def obtener_articulo_por_codigo(self, codigo):
        """Obtiene un artículo por código"""
        return self.repo.get_by_codigo(codigo)

    def obtener_por_codigo(self, codigo):
        """Alias para compatibilidad"""
        return self.obtener_articulo_por_codigo(codigo)

    def obtener_articulos_stock_bajo(self):
        """Obtiene artículos con stock bajo"""
        return self.repo.get_low_stock()

    def obtener_stock_bajo(self):
        """Alias para compatibilidad"""
        return self.obtener_articulos_stock_bajo()

    def crear_articulo(self, codigo, nombre, cantidad, valor_unitario, cuenta_contable, stock_min=0, stock_max=100, usuario_id=1):
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

    def obtener_articulo_por_id(self, articulo_id):
        """Obtiene un artículo por ID"""
        resultado = self.repo.get_by_id_with_item(articulo_id)
        if resultado:
            articulo, item = resultado
            return articulo
        return None

    def obtener_por_id(self, articulo_id):
        """Alias para compatibilidad"""
        return self.repo.get_by_id_with_item(articulo_id)

    def buscar_articulos(self, termino):
        """Busca artículos por nombre o código"""
        return self.repo.search_by_name_or_code(termino)

    def actualizar_articulo(self, articulo_id, **kwargs):
        """Actualiza un artículo"""
        return self.repo.update_with_item(articulo_id, **kwargs)

    def actualizar_valor_unitario(self, articulo_id, nuevo_valor, usuario_id, observaciones=None):
        """Actualiza el valor unitario de un artículo y registra el cambio"""
        from app.database.models import Item, MovimientoDetalle, Usuario
        from app import db
        from datetime import datetime
        
        # Obtener el artículo y su item
        resultado = self.repo.get_by_id_with_item(articulo_id)
        if not resultado:
            raise ValueError("Artículo no encontrado")
        
        articulo, item = resultado
        valor_anterior = float(item.i_vUnitario)
        
        # Solo actualizar si el valor es diferente
        if abs(valor_anterior - nuevo_valor) > 0.01:  # Tolerancia para decimales
            # Actualizar el valor unitario
            item.i_vUnitario = nuevo_valor
            # Recalcular valor total con el nuevo precio
            item.i_vTotal = item.i_cantidad * nuevo_valor
            
            db.session.commit()
            
            # Registrar el cambio en el historial
            usuario = Usuario.query.get(usuario_id) or Usuario.query.first()
            if usuario:
                movimiento = MovimientoDetalle(
                    m_fecha=datetime.now().date(),
                    m_tipo='ajuste_precio',
                    m_cantidad=0,  # Los ajustes de precio no afectan cantidad
                    m_valorUnitario=nuevo_valor,
                    m_valorTotal=0.0,
                    m_observaciones=f'Valor unitario actualizado de ${valor_anterior:.2f} a ${nuevo_valor:.2f}. {observaciones or ""}',
                    i_id=item.id,
                    u_id=usuario.id
                )
                
                db.session.add(movimiento)
                db.session.commit()
            
            return item
        else:
            return item

    def eliminar_articulo(self, articulo_id):
        """Elimina un artículo"""
        # Verificar que no tenga movimientos
        movimientos = self.movimiento_repo.get_by_item(articulo_id)
        if movimientos:
            raise ValueError("No se puede eliminar un artículo que tiene movimientos registrados")
        
        return self.repo.delete_with_item(articulo_id)

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