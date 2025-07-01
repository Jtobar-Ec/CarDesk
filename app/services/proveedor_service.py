from app.database.repositories.proveedores import ProveedorRepository
from app.database.models import Proveedor
from app.database import db

class ProveedorService:
    def __init__(self):
        self.repo = ProveedorRepository()

    def obtener_todos(self, incluir_inactivos=False):
        """Obtiene todos los proveedores"""
        if incluir_inactivos:
            return self.repo.get_all()
        else:
            return db.session.query(Proveedor).filter_by(p_estado='Activo').all()

    def obtener_por_p_estado(self, proveedor_p_estado):
        """Obtiene un proveedor por ID"""
        return self.repo.get_by_p_estado(proveedor_p_estado)

    def obtener_por_codigo(self, codigo):
        """Obtiene un proveedor por código"""
        return self.repo.get_by_codigo(codigo)

    def buscar_por_nombre(self, nombre):
        """Busca proveedores por nombre"""
        return self.repo.search_by_name(nombre)

    def _generar_codigo_proveedor(self):
        """Genera un código automático para proveedor"""
        # Buscar todos los códigos de proveedores existentes
        proveedores = db.session.query(Proveedor).filter(
            Proveedor.p_codigo.like('PROV%')
        ).all()
        
        # Extraer números de los códigos existentes
        numeros_existentes = []
        for proveedor in proveedores:
            try:
                numero_str = proveedor.p_codigo[4:]  # Quitar 'PROV'
                numero = int(numero_str)
                numeros_existentes.append(numero)
            except (ValueError, IndexError):
                continue
        
        # Encontrar el siguiente número disponible
        if numeros_existentes:
            numero = max(numeros_existentes) + 1
        else:
            numero = 1
        
        return f"PROV{numero:03d}"

    def crear_proveedor(self, razon_social, ci_ruc, direccion=None, telefono=None, correo=None):
        """Crea un nuevo proveedor con código automático"""
        codigo = self._generar_codigo_proveedor()
        
        return self.repo.create(
            p_codigo=codigo,
            p_razonsocial=razon_social,
            p_ci_ruc=ci_ruc,
            p_direccion=direccion,
            p_telefono=telefono,
            p_correo=correo
        )

    def actualizar_proveedor(self, proveedor_p_estado, **kwargs):
        """Actualiza un proveedor"""
        return self.repo.update(proveedor_p_estado, **kwargs)

    def cambiar_estado_proveedor(self, proveedor_id, nuevo_estado):
        """Cambia el estado de un proveedor (Activo/Inactivo)"""
        # Obtiene el proveedor por ID
        proveedor = self.repo.get_by_id(proveedor_id)
        
        # Verifica si el proveedor fue encontrado
        if not proveedor:
            print(f"Proveedor con id {proveedor_id} no encontrado.")
            return False  # No se encontró el proveedor
        
        # Cambia el estado
        print(f"Cambiando estado de {proveedor.p_razonsocial} ({proveedor.p_estado}) a {nuevo_estado}.")
        proveedor.p_estado = nuevo_estado
        
        try:
            # Confirma el cambio en la base de datos
            db.session.commit()
            print(f"Estado de {proveedor.p_razonsocial} actualizado a {nuevo_estado}.")
            return True  # Estado cambiado exitosamente
        except Exception as e:
            # Si ocurre algún error, realiza un rollback
            db.session.rollback()
            print(f"Error al cambiar el estado: {str(e)}")
            return False  # Error en la actualización
        
    def activar_proveedor(self, proveedor_p_estado):
        """Activa un proveedor"""
        return self.cambiar_estado_proveedor(proveedor_p_estado, 'Activo')

    def desactivar_proveedor(self, proveedor_p_estado):
        """Desactiva un proveedor"""
        return self.cambiar_estado_proveedor(proveedor_p_estado, 'Inactivo')

    def eliminar_proveedor(self, proveedor_p_estado):
        """Elimina un proveedor (mantener por compatibilp_estadoad, pero usar desactivar)"""
        return self.desactivar_proveedor(proveedor_p_estado)
    
    def obtener_por_id(self, proveedor_id):
        """Obtiene un proveedor por ID"""
        return db.session.query(Proveedor).get(proveedor_id)
    