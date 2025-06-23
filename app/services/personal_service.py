from app.database.repositories.personal import PersonalRepository
from app.database.models import Persona
from app.database import db

class PersonalService:
    def __init__(self):
        self.repo = PersonalRepository()

    def obtener_todos(self):
        """Obtiene todas las personas"""
        return self.repo.get_all()

    def obtener_por_id(self, persona_id):
        """Obtiene una persona por ID"""
        return self.repo.get_by_id(persona_id)

    def obtener_por_codigo(self, codigo):
        """Obtiene una persona por código"""
        return self.repo.get_by_codigo(codigo)

    def buscar_por_nombre(self, termino):
        """Busca personas por nombre o código"""
        return self.repo.search_by_name(termino)

    def obtener_activos(self):
        """Obtiene todas las personas activas"""
        return self.repo.get_activos()

    def obtener_por_cargo(self, cargo):
        """Obtiene personas por cargo"""
        return self.repo.get_by_cargo(cargo)

    def crear_persona(self, nombre, apellido=None, ci=None, telefono=None, correo=None,
                     direccion=None, cargo=None, estado='Activo'):
        """Crea una nueva persona con todos los campos"""
        # Generar código único
        codigo = self._generar_codigo_persona()
        
        # Crear nueva persona con todos los campos
        persona = Persona(
            pe_codigo=codigo,
            pe_nombre=nombre,
            pe_apellido=apellido,
            pe_ci=ci,
            pe_telefono=telefono,
            pe_correo=correo,
            pe_direccion=direccion,
            pe_cargo=cargo,
            pe_estado=estado
        )
        
        db.session.add(persona)
        db.session.commit()
        
        return persona

    def actualizar_persona(self, persona_id, **datos):
        """Actualiza una persona existente con todos los campos"""
        persona = self.obtener_por_id(persona_id)
        if not persona:
            return False
        
        # Actualizar todos los campos disponibles
        if 'nombre' in datos:
            persona.pe_nombre = datos['nombre']
        if 'apellido' in datos:
            persona.pe_apellido = datos['apellido']
        if 'ci' in datos:
            persona.pe_ci = datos['ci']
        if 'telefono' in datos:
            persona.pe_telefono = datos['telefono']
        if 'correo' in datos:
            persona.pe_correo = datos['correo']
        if 'direccion' in datos:
            persona.pe_direccion = datos['direccion']
        if 'cargo' in datos:
            persona.pe_cargo = datos['cargo']
        if 'estado' in datos:
            persona.pe_estado = datos['estado']
        
        db.session.commit()
        return True

    def eliminar_persona(self, persona_id):
        """Elimina una persona si no tiene consumos asociados"""
        persona = self.obtener_por_id(persona_id)
        if not persona:
            return False
        
        # Verificar si tiene consumos asociados
        if persona.consumos:
            raise ValueError("No se puede eliminar la persona porque tiene consumos asociados")
        
        db.session.delete(persona)
        db.session.commit()
        return True

    def cambiar_estado(self, persona_id, nuevo_estado):
        """Cambia el estado de una persona"""
        persona = self.obtener_por_id(persona_id)
        if not persona:
            return False
        
        persona.pe_estado = nuevo_estado
        db.session.commit()
        return True

    def _generar_codigo_persona(self):
        """Genera un código único para la persona (PER001, PER002, etc.)"""
        # Obtener el último código
        ultima_persona = Persona.query.filter(
            Persona.pe_codigo.like('PER%')
        ).order_by(Persona.pe_codigo.desc()).first()
        
        if ultima_persona:
            # Extraer el número del código (PER001 -> 001)
            try:
                ultimo_numero = int(ultima_persona.pe_codigo[3:])
                nuevo_numero = ultimo_numero + 1
            except (ValueError, IndexError):
                nuevo_numero = 1
        else:
            nuevo_numero = 1
        
        return f"PER{nuevo_numero:03d}"

    def obtener_cargos_disponibles(self):
        """Retorna la lista de cargos disponibles"""
        return [
            'Profesor',
            'Estudiante', 
            'Administrativo',
            'Director',
            'Coordinador',
            'Técnico',
            'Investigador'
        ]

    def obtener_estados_disponibles(self):
        """Retorna la lista de estados disponibles"""
        return ['Activo', 'Inactivo']

    # Métodos adicionales
    def obtener_por_ci(self, ci):
        """Obtiene una persona por CI"""
        return self.repo.get_by_ci(ci)