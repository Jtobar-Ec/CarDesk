from app.database.repositories.proveedores import ProveedorRepository

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

    def crear_proveedor(self, codigo, razon_social, ci_ruc, direccion=None, telefono=None, correo=None):
        """Crea un nuevo proveedor"""
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