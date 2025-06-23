from app.database.repositories.instrumentos import InstrumentoRepository
from app.database.repositories.movimientos import MovimientoRepository
from app.database.models import Item
from app.database import db

class InstrumentoService:
    def __init__(self):
        self.repo = InstrumentoRepository()
        self.movimiento_repo = MovimientoRepository()

    def obtener_todos(self):
        """Obtiene todos los instrumentos con su información de item"""
        return self.repo.get_all_with_items()

    def obtener_por_id(self, instrumento_id):
        """Obtiene un instrumento por ID"""
        return self.repo.get_by_id(instrumento_id)

    def obtener_por_serie(self, serie):
        """Obtiene un instrumento por número de serie"""
        return self.repo.get_by_serial(serie)

    def obtener_por_estado(self, estado):
        """Obtiene instrumentos por estado"""
        return self.repo.get_by_status(estado)

    def _generar_codigo_instrumento(self):
        """Genera un código automático para instrumento"""
        # Buscar todos los códigos de instrumentos existentes
        items = db.session.query(Item).filter(
            Item.i_tipo == 'instrumento',
            Item.i_codigo.like('INS%')
        ).all()
        
        # Extraer números de los códigos existentes
        numeros_existentes = []
        for item in items:
            try:
                numero_str = item.i_codigo[3:]  # Quitar 'INS'
                numero = int(numero_str)
                numeros_existentes.append(numero)
            except (ValueError, IndexError):
                continue
        
        # Encontrar el siguiente número disponible
        if numeros_existentes:
            numero = max(numeros_existentes) + 1
        else:
            numero = 1
        
        return f"INS{numero:03d}"

    def crear_instrumento(self, nombre, marca, modelo, serie, estado, valor_unitario=0):
        """Crea un nuevo instrumento con código automático"""
        try:
            # Verificar que la serie no exista
            if self.repo.get_by_serial(serie):
                raise ValueError(f"Ya existe un instrumento con la serie {serie}")
            
            # Generar código automático
            codigo = self._generar_codigo_instrumento()
            
            # Primero crear el item
            item = Item(
                i_codigo=codigo,
                i_nombre=nombre,
                i_tipo='instrumento',
                i_cantidad=1,  # Los instrumentos son únicos
                i_vUnitario=valor_unitario,
                i_vTotal=valor_unitario
            )
            db.session.add(item)
            db.session.flush()  # Para obtener el ID
            
            # Luego crear el instrumento
            instrumento = self.repo.create(
                i_id=item.id,
                i_marca=marca,
                i_modelo=modelo,
                i_serie=serie,
                i_estado=estado
            )
            
            db.session.commit()
            return instrumento
        except Exception as e:
            db.session.rollback()
            raise e

    def actualizar_instrumento(self, instrumento_id, marca=None, modelo=None, serie=None, estado=None):
        """Actualiza los datos de un instrumento"""
        try:
            # Si se está cambiando la serie, verificar que no exista
            if serie:
                existing = self.repo.get_by_serial(serie)
                if existing and existing.i_id != instrumento_id:
                    raise ValueError(f"Ya existe un instrumento con la serie {serie}")
            
            # Preparar datos para actualizar
            update_data = {}
            if marca is not None:
                update_data['i_marca'] = marca
            if modelo is not None:
                update_data['i_modelo'] = modelo
            if serie is not None:
                update_data['i_serie'] = serie
            if estado is not None:
                update_data['i_estado'] = estado
            
            return self.repo.update(instrumento_id, **update_data)
        except Exception as e:
            raise e

    def actualizar_estado(self, instrumento_id, nuevo_estado):
        """Actualiza el estado de un instrumento y registra el cambio en el historial"""
        # Obtener el instrumento actual para conocer el estado anterior
        instrumento = self.repo.get_by_id(instrumento_id)
        if not instrumento:
            raise ValueError("Instrumento no encontrado")
        
        estado_anterior = instrumento.i_estado
        
        # Solo actualizar si el estado es diferente
        if estado_anterior != nuevo_estado:
            # Actualizar el estado
            resultado = self.repo.update(instrumento_id, i_estado=nuevo_estado)
            
            # Registrar el cambio de estado en el historial de movimientos
            from app.database.models import Usuario, MovimientoDetalle
            from app.database import db
            from datetime import date
            
            # Obtener el primer usuario disponible (en una implementación real vendría de la sesión)
            usuario = Usuario.query.first()
            if usuario:
                movimiento = MovimientoDetalle(
                    m_fecha=date.today(),
                    m_tipo='cambio_estado',
                    m_cantidad=0,  # Los cambios de estado no afectan cantidad
                    m_valorUnitario=0.0,
                    m_valorTotal=0.0,
                    m_observaciones=f'Estado cambiado de "{estado_anterior}" a "{nuevo_estado}"',
                    i_id=instrumento.i_id,
                    u_id=usuario.id
                )
                
                db.session.add(movimiento)
                db.session.commit()
            
            return resultado
        else:
            # Si el estado es el mismo, no hacer nada
            return instrumento

    def eliminar_instrumento(self, instrumento_id):
        """Elimina un instrumento y su item asociado"""
        try:
            instrumento = self.repo.get_by_id(instrumento_id)
            if not instrumento:
                return False
            
            # Verificar que no tenga movimientos
            movimientos = self.movimiento_repo.get_by_item(instrumento.i_id)
            if movimientos:
                raise ValueError("No se puede eliminar un instrumento que tiene movimientos registrados")
            
            # Eliminar el item asociado (esto eliminará el instrumento por cascada)
            item = Item.query.get(instrumento.i_id)
            if item:
                db.session.delete(item)
            
            # Eliminar el instrumento
            db.session.delete(instrumento)
            db.session.commit()
            return True
        except Exception as e:
            db.session.rollback()
            raise e

    def obtener_movimientos(self, item_id):
        """Obtiene los movimientos de un instrumento"""
        return self.movimiento_repo.get_by_item(item_id)
    
    def registrar_entrada(self, instrumento_id, cantidad, valor_unitario, usuario_id, observaciones=None):
        """Registra una entrada de instrumento"""
        # Obtener el item_id del instrumento
        instrumento = self.repo.get_by_id(instrumento_id)
        if not instrumento:
            raise ValueError("Instrumento no encontrado")
        
        return self.movimiento_repo.crear_entrada(
            instrumento.i_id, cantidad, valor_unitario, usuario_id, observaciones=observaciones
        )
    
    def registrar_salida(self, instrumento_id, cantidad, valor_unitario, usuario_id, observaciones=None):
        """Registra una salida de instrumento"""
        # Obtener el item_id del instrumento
        instrumento = self.repo.get_by_id(instrumento_id)
        if not instrumento:
            raise ValueError("Instrumento no encontrado")
        
        return self.movimiento_repo.crear_salida(
            instrumento.i_id, cantidad, valor_unitario, usuario_id, observaciones=observaciones
        )

    def obtener_estados_disponibles(self):
        """Obtiene los estados disponibles para instrumentos"""
        return ['Disponible', 'En uso', 'Mantenimiento', 'Reparación', 'Fuera de servicio']