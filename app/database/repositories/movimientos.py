from .base import BaseRepository
from app.database.models import MovimientoDetalle, Item, Entrada, Consumo
from app.database import db
from datetime import datetime, date
from decimal import Decimal

class MovimientoRepository(BaseRepository):
    def __init__(self):
        super().__init__(MovimientoDetalle)
    
    def get_by_item(self, item_id):
        """Obtiene todos los movimientos de un item específico"""
        return MovimientoDetalle.query.filter_by(i_id=item_id).order_by(MovimientoDetalle.m_fecha.desc()).all()
    
    def get_by_date_range(self, fecha_inicio, fecha_fin):
        """Obtiene movimientos en un rango de fechas"""
        return MovimientoDetalle.query.filter(
            MovimientoDetalle.m_fecha >= fecha_inicio,
            MovimientoDetalle.m_fecha <= fecha_fin
        ).order_by(MovimientoDetalle.m_fecha.desc()).all()
    
    def get_by_tipo(self, tipo):
        """Obtiene movimientos por tipo (entrada, salida, ajuste)"""
        return MovimientoDetalle.query.filter_by(m_tipo=tipo).order_by(MovimientoDetalle.m_fecha.desc()).all()
    
    def crear_entrada(self, item_id, cantidad, valor_unitario, usuario_id, entrada_id=None, observaciones=None):
        """Crea un movimiento de entrada"""
        valor_unitario = Decimal(str(valor_unitario))
        valor_total = Decimal(str(cantidad)) * valor_unitario
        
        movimiento = MovimientoDetalle(
            m_fecha=date.today(),
            m_tipo='entrada',
            m_cantidad=cantidad,
            m_valorUnitario=valor_unitario,
            m_valorTotal=valor_total,
            m_observaciones=observaciones,
            i_id=item_id,
            e_id=entrada_id,
            u_id=usuario_id
        )
        
        # Actualizar stock del item
        item = Item.query.get(item_id)
        if item:
            # Calcular nuevo valor total ponderado
            valor_total_anterior = Decimal(str(item.i_vTotal))
            cantidad_anterior = item.i_cantidad
            
            # Actualizar cantidad
            item.i_cantidad += cantidad
            
            # Calcular nuevo valor unitario promedio ponderado
            if item.i_cantidad > 0:
                nuevo_valor_total = valor_total_anterior + valor_total
                item.i_vUnitario = nuevo_valor_total / item.i_cantidad
                item.i_vTotal = nuevo_valor_total
            else:
                item.i_vUnitario = valor_unitario
                item.i_vTotal = valor_total
        
        db.session.add(movimiento)
        db.session.commit()
        return movimiento
    
    def crear_salida(self, item_id, cantidad, valor_unitario, usuario_id, consumo_id=None, observaciones=None):
        """Crea un movimiento de salida"""
        # Verificar stock disponible
        item = Item.query.get(item_id)
        if not item or item.i_cantidad < cantidad:
            raise ValueError("Stock insuficiente")
        
        valor_unitario = Decimal(str(valor_unitario))
        valor_total = Decimal(str(cantidad)) * valor_unitario
        
        movimiento = MovimientoDetalle(
            m_fecha=date.today(),
            m_tipo='salida',
            m_cantidad=cantidad,
            m_valorUnitario=valor_unitario,
            m_valorTotal=valor_total,
            m_observaciones=observaciones,
            i_id=item_id,
            c_id=consumo_id,
            u_id=usuario_id
        )
        
        # Actualizar stock del item
        valor_total_salida = Decimal(str(item.i_vUnitario)) * Decimal(str(cantidad))
        item.i_cantidad -= cantidad
        
        if item.i_cantidad > 0:
            item.i_vTotal = Decimal(str(item.i_vTotal)) - valor_total_salida
            # Mantener el valor unitario actual (no recalcular en salidas)
        else:
            item.i_vUnitario = Decimal('0')
            item.i_vTotal = Decimal('0')
        
        db.session.add(movimiento)
        db.session.commit()
        return movimiento