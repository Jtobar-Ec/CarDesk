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
    u_password = db.Column(db.String(100), nullable=False)  # Almacenará el hash
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
    # Relaciones
    consumos = db.relationship('Consumo', backref='persona', lazy=True)
    
    
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
    entradas = db.relationship('Entrada', backref='proveedor', lazy=True)

class Item(BaseModel):
    __tablename__ = 'tb_item'
    
    i_codigo = db.Column(db.String(20), unique=True, nullable=False)
    i_nombre = db.Column(db.String(200), nullable=False)
    i_tipo = db.Column(db.String(20), nullable=False)  # 'instrumento' o 'articulo'
    i_cantidad = db.Column(db.Integer, default=0)
    i_vUnitario = db.Column(db.Numeric(10, 2), default=0.0)
    i_vTotal = db.Column(db.Numeric(10, 2), default=0.0)
    
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
    
    c_numero = db.Column(db.Integer, nullable=False)
    c_fecha = db.Column(db.Date, nullable=False)
    c_hora = db.Column(db.Time, nullable=False)
    c_descripcion = db.Column(db.String(200), nullable=False)
    pe_id = db.Column(db.Integer, db.ForeignKey('tb_persona.id'), nullable=False)
    movimientos = db.relationship('MovimientoDetalle', backref='consumo', lazy=True)

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
    
    m_fecha = db.Column(db.Date, nullable=False)
    m_tipo = db.Column(db.String(20), nullable=False)  # 'entrada', 'salida', 'ajuste'
    m_cantidad = db.Column(db.Integer, nullable=False)
    m_valorUnitario = db.Column(db.Numeric(10, 2), nullable=False)
    m_valorTotal = db.Column(db.Numeric(10, 2), nullable=False)
    m_observaciones = db.Column(db.String(200))
    i_id = db.Column(db.Integer, db.ForeignKey('tb_item.id'), nullable=False)
    e_id = db.Column(db.Integer, db.ForeignKey('tb_entrada.id'))
    c_id = db.Column(db.Integer, db.ForeignKey('tb_consumo.id'))
    u_id = db.Column(db.Integer, db.ForeignKey('tb_usuario.id'), nullable=False)