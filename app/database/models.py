from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from . import db

# Modelo Base (para funciones comunes)
class BaseModel(db.Model):
    __abstract__ = True
    
    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def save(self):
        db.session.add(self)
        db.session.commit()

    def delete(self):
        db.session.delete(self)
        db.session.commit()

# Tablas según tu estructura
class Usuario(UserMixin, BaseModel):
    __tablename__ = 'tb_usuario'
    
    u_username = db.Column(db.String(50), unique=True, nullable=False)
    u_password = db.Column(db.String(255), nullable=False)  # Almacenará el hash
    u_codigo_dactilar = db.Column(db.String(255), nullable=True)  # Código dactilar para recuperación
    movimientos = db.relationship('MovimientoDetalle', backref='usuario', lazy=True)
    
    def set_password(self, password):
        """Establece la contraseña hasheada"""
        self.u_password = generate_password_hash(password)
    
    def check_password(self, password):
        """Verifica la contraseña"""
        return check_password_hash(self.u_password, password)
    
    def get_id(self):
        """Requerido por Flask-Login"""
        return str(self.id)
    
    @property
    def username(self):
        """Propiedad para acceder al username más fácilmente"""
        return self.u_username

class Persona(BaseModel):
    __tablename__ = 'tb_persona'
    
    pe_codigo = db.Column(db.String(20), unique=True, nullable=False)
    pe_nombre = db.Column(db.String(100), nullable=False)
    pe_apellido = db.Column(db.String(100))
    pe_ci = db.Column(db.String(20))
    pe_telefono = db.Column(db.String(15))
    pe_correo = db.Column(db.String(100))
    pe_direccion = db.Column(db.String(200))
    pe_cargo = db.Column(db.String(50))
    pe_estado = db.Column(db.String(20), default='Activo')
    
    
    def get_nombre_completo(self):
        """Retorna el nombre completo"""
        return self.pe_nombre
    
    def get_primer_nombre(self):
        """Retorna solo el primer nombre"""
        return self.pe_nombre.split(' ')[0] if self.pe_nombre else ''

class Proveedor(BaseModel):
    __tablename__ = 'tb_proveedores'
    
    p_codigo = db.Column(db.String(20), unique=True, nullable=False)
    p_razonsocial = db.Column(db.String(100), nullable=False)
    p_ci_ruc = db.Column(db.String(13), nullable=False)
    p_direccion = db.Column(db.String(200))
    p_telefono = db.Column(db.String(15))
    p_correo = db.Column(db.String(100))
    p_estado = db.Column(db.String(20), default='Activo')  # Activo, Inactivo
    entradas = db.relationship('Entrada', backref='proveedor', lazy=True)

class Item(BaseModel):
    __tablename__ = 'tb_item'
    
    i_codigo = db.Column(db.String(20), unique=True, nullable=False)
    i_nombre = db.Column(db.String(200), nullable=False)
    i_tipo = db.Column(db.String(20), nullable=False)  # 'instrumento' o 'articulo'
    i_cantidad = db.Column(db.Integer, default=0)
    i_vUnitario = db.Column(db.Numeric(10, 2), default=0.0)
    i_vTotal = db.Column(db.Numeric(10, 2), default=0.0)
    i_serial = db.Column(db.String(100), nullable=True)  # Número de serie opcional
    i_codigo_identificacion = db.Column(db.String(100), nullable=True)  # Código de identificación opcional
    i_estado = db.Column(db.String(20), default='Activo')  # Activo, Dañado, Baja
    i_observaciones_estado = db.Column(db.String(500), nullable=True)  # Observaciones del estado
    
    # Relación polimórfica
    instrumento = db.relationship('Instrumento', backref='item', uselist=False)
    articulo = db.relationship('Articulo', backref='item', uselist=False)
    movimientos = db.relationship('MovimientoDetalle', backref='item', lazy=True)
    stock = db.relationship('Stock', backref='item', uselist=False)

class Instrumento(db.Model):
    __tablename__ = 'tb_instrumento'
    
    i_id = db.Column(db.Integer, db.ForeignKey('tb_item.id'), primary_key=True)
    i_marca = db.Column(db.String(50), nullable=False)
    i_modelo = db.Column(db.String(50), nullable=False)
    i_serie = db.Column(db.String(50), unique=True, nullable=False)
    i_estado = db.Column(db.String(50), nullable=False)  # Podría ser un Enum
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def save(self):
        db.session.add(self)
        db.session.commit()

    def delete(self):
        db.session.delete(self)
        db.session.commit()

class Articulo(db.Model):
    __tablename__ = 'tb_articulo'
    
    i_id = db.Column(db.Integer, db.ForeignKey('tb_item.id'), primary_key=True)
    a_c_contable = db.Column(db.String(20), nullable=False)
    a_stockMax = db.Column(db.Integer)
    a_stockMin = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def save(self):
        db.session.add(self)
        db.session.commit()

    def delete(self):
        db.session.delete(self)
        db.session.commit()

class Stock(BaseModel):
    __tablename__ = 'tb_stock'
    
    s_cantidad = db.Column(db.Integer, default=0)
    s_ultUpdt = db.Column(db.DateTime, default=datetime.utcnow)
    i_id = db.Column(db.Integer, db.ForeignKey('tb_item.id'), nullable=False)

class Consumo(BaseModel):
    __tablename__ = 'tb_consumo'
    
    c_numero = db.Column(db.Integer, nullable=False, default=1)
    c_fecha = db.Column(db.Date, nullable=False)
    c_hora = db.Column(db.Time, nullable=False)
    c_descripcion = db.Column(db.String(200), nullable=False, default='Asignación de artículo')
    c_cantidad = db.Column(db.Integer, nullable=False)
    c_valorUnitario = db.Column(db.Numeric(10, 2), nullable=False)
    c_valorTotal = db.Column(db.Numeric(10, 2), nullable=False)
    c_observaciones = db.Column(db.String(500))
    c_estado = db.Column(db.String(20), default='Asignado')  # Asignado, Devuelto, Perdido, Dañado, Finalizado
    c_fecha_devolucion = db.Column(db.DateTime)  # Fecha cuando se marcó como devuelto
    c_puede_editar = db.Column(db.Boolean, default=True)  # Si se puede editar (48 horas)
    pe_id = db.Column(db.Integer, db.ForeignKey('tb_persona.id'), nullable=False)
    i_id = db.Column(db.Integer, db.ForeignKey('tb_item.id'), nullable=False)
    u_id = db.Column(db.Integer, db.ForeignKey('tb_usuario.id'), nullable=False)
    
    # Relaciones
    persona = db.relationship('Persona', backref='consumos')
    item = db.relationship('Item', backref='consumos')
    usuario = db.relationship('Usuario', backref='consumos_usuario')
    
    @property
    def c_id(self):
        """Alias para compatibilidad con templates"""
        return self.id
    
    @property
    def puede_editar_por_tiempo(self):
        """Verifica si la asignación puede editarse (dentro de 48 horas)"""
        from datetime import datetime, timedelta
        if not self.created_at:
            return False
        
        limite_edicion = self.created_at + timedelta(hours=48)
        return datetime.utcnow() <= limite_edicion
    
    @property
    def tiempo_restante_edicion(self):
        """Retorna el tiempo restante para poder editar"""
        from datetime import datetime, timedelta
        if not self.created_at:
            return None
        
        limite_edicion = self.created_at + timedelta(hours=48)
        tiempo_restante = limite_edicion - datetime.utcnow()
        
        if tiempo_restante.total_seconds() <= 0:
            return None
        
        horas = int(tiempo_restante.total_seconds() // 3600)
        minutos = int((tiempo_restante.total_seconds() % 3600) // 60)
        
        return f"{horas}h {minutos}m"

class Entrada(BaseModel):
    __tablename__ = 'tb_entrada'
    
    e_fecha = db.Column(db.Date, nullable=False)
    e_hora = db.Column(db.Time, nullable=False)
    e_descripcion = db.Column(db.String(200), nullable=False)
    e_numFactura = db.Column(db.String(20), nullable=False)
    p_id = db.Column(db.Integer, db.ForeignKey('tb_proveedores.id'), nullable=False)
    movimientos = db.relationship('MovimientoDetalle', backref='entrada', lazy=True)

class MovimientoDetalle(BaseModel):
    __tablename__ = 'tb_movimiento_detalle'
    
    m_fecha = db.Column(db.DateTime, nullable=False)
    m_tipo = db.Column(db.String(20), nullable=False)  # 'entrada', 'salida', 'ajuste'
    m_cantidad = db.Column(db.Integer, nullable=False)
    m_valorUnitario = db.Column(db.Numeric(10, 2), nullable=False)
    m_valorTotal = db.Column(db.Numeric(10, 2), nullable=False)
    m_observaciones = db.Column(db.String(200))
    # Campos para auditoría mejorada
    m_stock_anterior = db.Column(db.Integer)  # Stock antes del movimiento
    m_stock_actual = db.Column(db.Integer)    # Stock después del movimiento
    m_valor_anterior = db.Column(db.Numeric(10, 2))  # Valor unitario anterior
    m_valor_actual = db.Column(db.Numeric(10, 2))    # Valor unitario actual
    i_id = db.Column(db.Integer, db.ForeignKey('tb_item.id'), nullable=False)
    e_id = db.Column(db.Integer, db.ForeignKey('tb_entrada.id'))
    c_id = db.Column(db.Integer, db.ForeignKey('tb_consumo.id'))
    u_id = db.Column(db.Integer, db.ForeignKey('tb_usuario.id'), nullable=False)