from app.database.repositories.proveedores import ProveedorRepository
from app.database.models import Proveedor
from app.database import db

class ProveedorService:
    def __init__(self):
        self.repo = ProveedorRepository()

    def obtener_todos(self):
        """Obtiene todos los proveedores"""
        return self.repo.get_all()

    def obtener_por_id(self, proveedor_id):
        """Obtiene un proveedor por ID"""
        return self.repo.get_by_id(proveedor_id)

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

    def actualizar_proveedor(self, proveedor_id, **kwargs):
        """Actualiza un proveedor"""
        return self.repo.update(proveedor_id, **kwargs)

    def eliminar_proveedor(self, proveedor_id):
        """Elimina un proveedor"""
        return self.repo.delete(proveedor_id)