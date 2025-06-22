#!/usr/bin/env python3
"""
Script para verificar la funcionalidad CRUD del sistema Kardex
"""

import sys
from os.path import abspath, dirname

# Añade el directorio del proyecto al PYTHONPATH
sys.path.insert(0, dirname(abspath(__file__)))

from app import create_app
from app.services import InstrumentoService, ArticuloService, ProveedorService

def test_proveedores_crud():
    """Prueba las operaciones CRUD de proveedores"""
    print("\n=== TESTING PROVEEDORES CRUD ===")
    
    service = ProveedorService()
    
    # READ - Listar todos los proveedores
    print("1. READ - Listando todos los proveedores:")
    proveedores = service.obtener_todos()
    for proveedor in proveedores:
        print(f"   - {proveedor.p_codigo}: {proveedor.p_razonsocial}")
    
    # CREATE - Crear nuevo proveedor
    print("\n2. CREATE - Creando nuevo proveedor:")
    try:
        nuevo_proveedor = service.crear_proveedor(
            codigo="PROV004",
            razon_social="Nuevo Proveedor Test S.A.",
            ci_ruc="1111111111111",
            direccion="Dirección de prueba",
            telefono="0999999999",
            correo="test@proveedor.com"
        )
        print(f"   ✓ Proveedor creado: {nuevo_proveedor.p_codigo} - {nuevo_proveedor.p_razonsocial}")
    except Exception as e:
        print(f"   ✗ Error al crear proveedor: {e}")
    
    # READ - Buscar por código
    print("\n3. READ - Buscando proveedor por código:")
    proveedor = service.obtener_por_codigo("PROV001")
    if proveedor:
        print(f"   ✓ Encontrado: {proveedor.p_codigo} - {proveedor.p_razonsocial}")
    else:
        print("   ✗ No encontrado")
    
    # UPDATE - Actualizar proveedor
    print("\n4. UPDATE - Actualizando proveedor:")
    try:
        proveedor_actualizado = service.actualizar_proveedor(
            nuevo_proveedor.id,
            p_telefono="0888888888",
            p_correo="nuevo@email.com"
        )
        if proveedor_actualizado:
            print(f"   ✓ Proveedor actualizado: {proveedor_actualizado.p_telefono}")
        else:
            print("   ✗ No se pudo actualizar")
    except Exception as e:
        print(f"   ✗ Error al actualizar: {e}")
    
    # DELETE - Eliminar proveedor
    print("\n5. DELETE - Eliminando proveedor de prueba:")
    try:
        eliminado = service.eliminar_proveedor(nuevo_proveedor.id)
        if eliminado:
            print("   ✓ Proveedor eliminado exitosamente")
        else:
            print("   ✗ No se pudo eliminar")
    except Exception as e:
        print(f"   ✗ Error al eliminar: {e}")

def test_articulos_crud():
    """Prueba las operaciones CRUD de artículos"""
    print("\n=== TESTING ARTÍCULOS CRUD ===")
    
    service = ArticuloService()
    
    # READ - Listar todos los artículos
    print("1. READ - Listando todos los artículos:")
    articulos = service.obtener_todos()
    for articulo, item in articulos:
        print(f"   - {item.i_codigo}: {item.i_nombre} (Stock: {item.i_cantidad})")
    
    # CREATE - Crear nuevo artículo
    print("\n2. CREATE - Creando nuevo artículo:")
    try:
        nuevo_articulo, nuevo_item = service.crear_articulo(
            codigo="ART006",
            nombre="Artículo de Prueba",
            cantidad=50,
            valor_unitario=25.00,
            cuenta_contable="5101006",
            stock_min=10,
            stock_max=100
        )
        print(f"   ✓ Artículo creado: {nuevo_item.i_codigo} - {nuevo_item.i_nombre}")
    except Exception as e:
        print(f"   ✗ Error al crear artículo: {e}")
        return
    
    # READ - Buscar por código
    print("\n3. READ - Buscando artículo por código:")
    resultado = service.obtener_por_codigo("ART001")
    if resultado:
        articulo, item = resultado
        print(f"   ✓ Encontrado: {item.i_codigo} - {item.i_nombre}")
    else:
        print("   ✗ No encontrado")
    
    # READ - Artículos con stock bajo
    print("\n4. READ - Artículos con stock bajo:")
    stock_bajo = service.obtener_stock_bajo()
    for articulo, item in stock_bajo:
        print(f"   - {item.i_codigo}: {item.i_nombre} (Stock: {item.i_cantidad}, Mín: {articulo.a_stockMin})")

def test_instrumentos_crud():
    """Prueba las operaciones CRUD de instrumentos"""
    print("\n=== TESTING INSTRUMENTOS CRUD ===")
    
    service = InstrumentoService()
    
    # READ - Listar todos los instrumentos
    print("1. READ - Listando todos los instrumentos:")
    instrumentos = service.obtener_todos()
    for instrumento in instrumentos:
        print(f"   - {instrumento.i_serie}: {instrumento.item.i_nombre} ({instrumento.i_estado})")
    
    # CREATE - Crear nuevo instrumento
    print("\n2. CREATE - Creando nuevo instrumento:")
    try:
        nuevo_instrumento = service.crear_instrumento(
            codigo="INST004",
            nombre="Instrumento de Prueba",
            marca="Marca Test",
            modelo="Modelo Test",
            serie="TEST001",
            estado="Disponible",
            valor_unitario=500.00
        )
        print(f"   ✓ Instrumento creado: {nuevo_instrumento.i_serie} - {nuevo_instrumento.item.i_nombre}")
    except Exception as e:
        print(f"   ✗ Error al crear instrumento: {e}")
        return
    
    # READ - Buscar por serie
    print("\n3. READ - Buscando instrumento por serie:")
    instrumento = service.obtener_por_serie("YV001234")
    if instrumento:
        print(f"   ✓ Encontrado: {instrumento.i_serie} - {instrumento.item.i_nombre}")
    else:
        print("   ✗ No encontrado")
    
    # UPDATE - Actualizar estado
    print("\n4. UPDATE - Actualizando estado del instrumento:")
    try:
        instrumento_actualizado = service.actualizar_estado(nuevo_instrumento.i_id, "En mantenimiento")
        if instrumento_actualizado:
            print(f"   ✓ Estado actualizado: {instrumento_actualizado.i_estado}")
        else:
            print("   ✗ No se pudo actualizar")
    except Exception as e:
        print(f"   ✗ Error al actualizar: {e}")
    
    # READ - Buscar por estado
    print("\n5. READ - Instrumentos disponibles:")
    disponibles = service.obtener_por_estado("Disponible")
    for instrumento in disponibles:
        print(f"   - {instrumento.i_serie}: {instrumento.item.i_nombre}")

def main():
    """Función principal"""
    app = create_app()
    
    with app.app_context():
        print("🧪 INICIANDO PRUEBAS CRUD DEL SISTEMA KARDEX")
        print("=" * 50)
        
        try:
            # Probar CRUD de proveedores
            test_proveedores_crud()
            
            # Probar CRUD de artículos
            test_articulos_crud()
            
            # Probar CRUD de instrumentos
            test_instrumentos_crud()
            
            print("\n" + "=" * 50)
            print("✅ PRUEBAS COMPLETADAS")
            
        except Exception as e:
            print(f"\n❌ ERROR DURANTE LAS PRUEBAS: {e}")
            import traceback
            traceback.print_exc()

if __name__ == '__main__':
    main()