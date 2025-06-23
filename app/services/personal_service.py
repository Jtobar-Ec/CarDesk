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

    def obtener_por_ci(self, ci):
        """Obtiene una persona por CI"""
        return self.repo.get_by_ci(ci)

    def obtener_activos(self):
        """Obtiene solo las personas activas"""
        return self.repo.get_activos()

    def obtener_por_cargo(self, cargo):
        """Obtiene personas por cargo"""
        return self.repo.get_by_cargo(cargo)

    def buscar_por_nombre(self, termino):
        """Busca personas por nombre, apellido o código"""
        return self.repo.search_by_name(termino)

    def _generar_codigo_persona(self):
        """Genera un código automático para persona"""
        # Buscar todos los códigos de personas existentes
        personas = db.session.query(Persona).filter(
            Persona.pe_codigo.like('PER%')
        ).all()
        
        # Extraer números de los códigos existentes
        numeros_existentes = []
        for persona in personas:
            try:
                numero_str = persona.pe_codigo[3:]  # Quitar 'PER'
                numero = int(numero_str)
                numeros_existentes.append(numero)
            except (ValueError, IndexError):
                continue
        
        # Encontrar el siguiente número disponible
        if numeros_existentes:
            numero = max(numeros_existentes) + 1
        else:
            numero = 1
        
        return f"PER{numero:03d}"

    def crear_persona(self, nombre, apellido, ci, telefono=None, correo=None, 
                     direccion=None, cargo=None, estado='Activo'):
        """Crea una nueva persona con código automático"""
        # Verificar que la CI no exista
        if self.repo.get_by_ci(ci):
            raise ValueError(f"Ya existe una persona con la CI {ci}")
        
        codigo = self._generar_codigo_persona()
        
        return self.repo.create(
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

    def actualizar_persona(self, persona_id, **kwargs):
        """Actualiza una persona"""
        # Si se está cambiando la CI, verificar que no exista
        if 'pe_ci' in kwargs:
            existing = self.repo.get_by_ci(kwargs['pe_ci'])
            if existing and existing.id != persona_id:
                raise ValueError(f"Ya existe una persona con la CI {kwargs['pe_ci']}")
        
        return self.repo.update(persona_id, **kwargs)

    def eliminar_persona(self, persona_id):
        """Elimina una persona"""
        # Verificar que no tenga consumos
        persona = self.repo.get_by_id(persona_id)
        if persona and persona.consumos:
            raise ValueError("No se puede eliminar una persona que tiene consumos registrados")
        
        return self.repo.delete(persona_id)

    def cambiar_estado(self, persona_id, nuevo_estado):
        """Cambia el estado de una persona"""
        return self.actualizar_persona(persona_id, pe_estado=nuevo_estado)

    def obtener_cargos_disponibles(self):
        """Obtiene los cargos disponibles"""
        return ['Profesor', 'Estudiante', 'Administrativo', 'Director', 'Coordinador', 'Auxiliar', 'Otro']

    def obtener_estados_disponibles(self):
        """Obtiene los estados disponibles"""
        return ['Activo', 'Inactivo']