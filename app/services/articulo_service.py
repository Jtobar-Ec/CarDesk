from app.database.repositories.articulos import ArticuloRepository
from app.database.repositories.movimientos import MovimientoRepository
from app.database.models import Item
from app.database import db
def _registrar_movimiento_con_auditoria(item_id, tipo, cantidad, valor_unitario, usuario_id, observaciones=None, entrada_id=None, consumo_id=None):
    """Registra un movimiento con auditoría completa de valores anteriores y actuales"""
    from app.database.models import MovimientoDetalle
    
    item = Item.query.get(item_id)
    if not item:
        raise ValueError("Item no encontrado")
    
    # Capturar valores anteriores
    stock_anterior = item.i_cantidad
    valor_anterior = float(item.i_vUnitario)
    
    # Calcular nuevos valores
    if tipo == 'entrada':
        stock_actual = stock_anterior + cantidad
    elif tipo == 'salida':
        stock_actual = stock_anterior - cantidad
    else:  # ajuste
        stock_actual = cantidad
    
    valor_actual = float(valor_unitario)
    valor_total = cantidad * valor_unitario
    
    # Crear movimiento con auditoría
    movimiento = MovimientoDetalle(
        m_fecha=datetime.now().date(),
        m_tipo=tipo,
        m_cantidad=cantidad,
        m_valorUnitario=valor_unitario,
        m_valorTotal=valor_total,
        m_observaciones=observaciones,
        m_stock_anterior=stock_anterior,
        m_stock_actual=stock_actual,
        m_valor_anterior=valor_anterior,
        m_valor_actual=valor_actual,
        i_id=item_id,
        e_id=entrada_id,
        c_id=consumo_id,
        u_id=usuario_id
    )
    
    # Actualizar item
    item.i_cantidad = stock_actual
    item.i_vUnitario = valor_unitario
    item.i_vTotal = stock_actual * valor_unitario
    
    db.session.add(movimiento)
    db.session.commit()
    
    return movimiento


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

    def _generar_codigo_articulo(self):
        """Genera un código automático para artículo"""
        # Buscar todos los códigos de artículos existentes
        items = db.session.query(Item).filter(
            Item.i_tipo == 'articulo',
            Item.i_codigo.like('ART%')
        ).all()
        
        # Extraer números de los códigos existentes
        numeros_existentes = []
        for item in items:
            try:
                numero_str = item.i_codigo[3:]  # Quitar 'ART'
                numero = int(numero_str)
                numeros_existentes.append(numero)
            except (ValueError, IndexError):
                continue
        
        # Encontrar el siguiente número disponible
        if numeros_existentes:
            numero = max(numeros_existentes) + 1
        else:
            numero = 1
        
        return f"ART{numero:03d}"

    def crear_articulo(self, nombre, cantidad, valor_unitario, cuenta_contable, stock_min=0, stock_max=100, usuario_id=1):
        """Crea un nuevo artículo con código automático"""
        codigo = self._generar_codigo_articulo()
        
        # Crear artículo sin stock inicial (se agregará con entrada si es necesario)
        item_data = {
            'i_codigo': codigo,
            'i_nombre': nombre,
            'i_tipo': 'articulo',
            'i_cantidad': 0,  # Iniciar en 0, se agregará stock con entrada
            'i_vUnitario': valor_unitario,
            'i_vTotal': 0  # Iniciar en 0
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

    def registrar_entrada(self, articulo_id, cantidad, valor_unitario, usuario_id, proveedor_id=None, observaciones=None, fecha_hora=None):
        """Registra una entrada de artículo con proveedor"""
        from app.database.models import Entrada
        from app import db
        from datetime import datetime
        
        if fecha_hora is None:
            fecha_hora = datetime.now()
        
        # Crear registro de entrada si se especifica proveedor
        entrada_id = None
        if proveedor_id:
            entrada = Entrada(
                e_fecha=fecha_hora.date(),
                e_hora=fecha_hora.time(),
                e_descripcion=observaciones or f"Entrada de artículo - Cantidad: {cantidad}",
                e_numFactura=f"AUTO-{fecha_hora.strftime('%Y%m%d%H%M%S')}",
                p_id=proveedor_id
            )
            db.session.add(entrada)
            db.session.flush()  # Para obtener el ID
            entrada_id = entrada.id
        
        return self.movimiento_repo.crear_entrada(
            articulo_id, cantidad, valor_unitario, usuario_id,
            entrada_id=entrada_id, observaciones=observaciones, fecha_hora=fecha_hora
        )

    def registrar_salida(self, articulo_id, cantidad, valor_unitario, usuario_id, observaciones=None):
        """Registra una salida de artículo"""
        return self.movimiento_repo.crear_salida(
            articulo_id, cantidad, valor_unitario, usuario_id, observaciones=observaciones
        )

    def registrar_salida_con_asignacion(self, articulo_id, cantidad, valor_unitario, usuario_id, persona_id, observaciones=None):
        """Registra una salida de artículo con asignación a personal"""
        from app.database.models import Consumo, Persona, MovimientoDetalle
        from app import db
        from datetime import datetime
        
        # Obtener el artículo y su item para usar el ID correcto
        resultado = self.repo.get_by_id_with_item(articulo_id)
        if not resultado:
            raise ValueError("Artículo no encontrado")
        
        articulo, item = resultado
        item_id = item.id
        
        # Verificar que la persona existe y está activa
        persona = Persona.query.get(persona_id)
        if not persona:
            raise ValueError("La persona seleccionada no existe")
        
        if persona.pe_estado != 'Activo':
            raise ValueError("Solo se puede asignar artículos a personal activo")
        
        # Crear registro de consumo (asignación) primero
        consumo = Consumo(
            c_numero=1,  # Número secuencial por consumo
            c_fecha=datetime.now().date(),
            c_hora=datetime.now().time(),
            c_descripcion=f"Asignación de {cantidad} unidades de artículo a {persona.pe_nombre}",
            c_cantidad=cantidad,
            c_valorUnitario=valor_unitario,
            c_valorTotal=cantidad * valor_unitario,
            c_observaciones=observaciones or f"Artículo asignado para uso de {persona.pe_cargo or 'personal'}",
            c_estado='Asignado',
            pe_id=persona_id,
            i_id=item_id,
            u_id=usuario_id
        )
        
        db.session.add(consumo)
        db.session.flush()  # Para obtener el ID del consumo
        
        # Crear movimiento detalle vinculado al consumo
        movimiento = MovimientoDetalle(
            m_fecha=datetime.now().date(),
            m_tipo='salida',
            m_cantidad=cantidad,
            m_valorUnitario=valor_unitario,
            m_valorTotal=cantidad * valor_unitario,
            m_observaciones=f"Asignado a: {persona.pe_nombre} {persona.pe_apellido or ''} - {observaciones or ''}",
            i_id=item_id,
            c_id=consumo.id,  # Vincular con el consumo
            u_id=usuario_id
        )
        
        db.session.add(movimiento)
        
        # Actualizar stock del artículo
        if item.i_cantidad >= cantidad:
            item.i_cantidad -= cantidad
            item.i_vTotal = item.i_cantidad * item.i_vUnitario
        else:
            raise ValueError(f"Stock insuficiente. Disponible: {item.i_cantidad}, Solicitado: {cantidad}")
        
        db.session.commit()
        
        return movimiento, consumo

    def registrar_movimiento_devolucion(self, item_id, cantidad, valor_unitario, usuario_id, observaciones=None):
        """Registra un movimiento de entrada por devolución"""
        from app.database.models import MovimientoDetalle
        from app import db
        from datetime import datetime
        
        movimiento = MovimientoDetalle(
            m_fecha=datetime.now().date(),
            m_tipo='entrada',
            m_cantidad=cantidad,
            m_valorUnitario=valor_unitario,
            m_valorTotal=cantidad * valor_unitario,
            m_observaciones=f"DEVOLUCIÓN: {observaciones or 'Artículo devuelto al inventario'}",
            i_id=item_id,
            u_id=usuario_id
        )
        
        db.session.add(movimiento)
        db.session.commit()
        
        return movimiento

    def registrar_movimiento_salida(self, item_id, cantidad, valor_unitario, usuario_id, observaciones=None):
        """Registra un movimiento de salida por reasignación"""
        from app.database.models import MovimientoDetalle
        from app import db
        from datetime import datetime
        
        movimiento = MovimientoDetalle(
            m_fecha=datetime.now().date(),
            m_tipo='salida',
            m_cantidad=cantidad,
            m_valorUnitario=valor_unitario,
            m_valorTotal=cantidad * valor_unitario,
            m_observaciones=f"REASIGNACIÓN: {observaciones or 'Artículo reasignado desde devolución'}",
            i_id=item_id,
            u_id=usuario_id
        )
        
        db.session.add(movimiento)
        db.session.commit()
        
        return movimiento
    