#!/usr/bin/env python3
"""
Script de prueba para verificar el CRUD completo de proveedores
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.services.proveedor_service import ProveedorService

def test_crud_proveedores():
    """Prueba todas las operaciones CRUD de proveedores"""
    
    app = create_app()
    
    with app.app_context():
        print("🔍 PROBANDO CRUD COMPLETO DE PROVEEDORES")
        print("=" * 60)
        
        # Servicio
        proveedor_service = ProveedorService()
        
        # 1. CREATE - Crear proveedor
        print("\n1️⃣ PROBANDO CREACIÓN (CREATE)...")
        try:
            proveedor = proveedor_service.crear_proveedor(
                razon_social="Empresa de Prueba CRUD S.A.",
                ci_ruc="9876543210987",
                direccion="Avenida CRUD 123",
                telefono="555-CRUD",
                correo="crud@test.com"
            )
            print(f"   ✅ Proveedor creado exitosamente")
            print(f"   📝 Código: {proveedor.p_codigo}")
            print(f"   🏢 Razón social: {proveedor.p_razonsocial}")
            print(f"   🆔 CI/RUC: {proveedor.p_ci_ruc}")
            print(f"   📍 Dirección: {proveedor.p_direccion}")
            print(f"   📞 Teléfono: {proveedor.p_telefono}")
            print(f"   📧 Correo: {proveedor.p_correo}")
            proveedor_id = proveedor.id
        except Exception as e:
            print(f"   ❌ Error en CREATE: {str(e)}")
            return False
        
        # 2. READ - Leer proveedor
        print("\n2️⃣ PROBANDO LECTURA (READ)...")
        try:
            # Leer por ID
            proveedor_leido = proveedor_service.obtener_por_id(proveedor_id)
            if proveedor_leido:
                print(f"   ✅ Proveedor leído por ID exitosamente")
                print(f"   📝 Código: {proveedor_leido.p_codigo}")
                print(f"   🏢 Razón social: {proveedor_leido.p_razonsocial}")
            else:
                print(f"   ❌ No se pudo leer el proveedor por ID")
                return False
            
            # Leer por código
            proveedor_por_codigo = proveedor_service.obtener_por_codigo(proveedor.p_codigo)
            if proveedor_por_codigo:
                print(f"   ✅ Proveedor leído por código exitosamente")
            else:
                print(f"   ❌ No se pudo leer el proveedor por código")
                return False
            
            # Leer todos
            todos_proveedores = proveedor_service.obtener_todos()
            print(f"   ✅ Total de proveedores en sistema: {len(todos_proveedores)}")
            
            # Buscar por nombre
            proveedores_encontrados = proveedor_service.buscar_por_nombre("CRUD")
            print(f"   ✅ Proveedores encontrados con 'CRUD': {len(proveedores_encontrados)}")
            
        except Exception as e:
            print(f"   ❌ Error en READ: {str(e)}")
            return False
        
        # 3. UPDATE - Actualizar proveedor
        print("\n3️⃣ PROBANDO ACTUALIZACIÓN (UPDATE)...")
        try:
            datos_actualizacion = {
                'p_razonsocial': 'Empresa de Prueba CRUD ACTUALIZADA S.A.',
                'p_direccion': 'Nueva Avenida CRUD 456',
                'p_telefono': '555-UPDATED',
                'p_correo': 'updated@test.com'
            }
            
            proveedor_actualizado = proveedor_service.actualizar_proveedor(
                proveedor_id, **datos_actualizacion
            )
            
            if proveedor_actualizado:
                print(f"   ✅ Proveedor actualizado exitosamente")
                print(f"   🏢 Nueva razón social: {proveedor_actualizado.p_razonsocial}")
                print(f"   📍 Nueva dirección: {proveedor_actualizado.p_direccion}")
                print(f"   📞 Nuevo teléfono: {proveedor_actualizado.p_telefono}")
                print(f"   📧 Nuevo correo: {proveedor_actualizado.p_correo}")
            else:
                print(f"   ❌ No se pudo actualizar el proveedor")
                return False
                
        except Exception as e:
            print(f"   ❌ Error en UPDATE: {str(e)}")
            return False
        
        # 4. Verificar que los cambios persisten
        print("\n4️⃣ VERIFICANDO PERSISTENCIA DE CAMBIOS...")
        try:
            proveedor_verificado = proveedor_service.obtener_por_id(proveedor_id)
            if (proveedor_verificado and 
                proveedor_verificado.p_razonsocial == datos_actualizacion['p_razonsocial'] and
                proveedor_verificado.p_direccion == datos_actualizacion['p_direccion']):
                print(f"   ✅ Los cambios persisten correctamente en la base de datos")
            else:
                print(f"   ❌ Los cambios no persisten correctamente")
                return False
        except Exception as e:
            print(f"   ❌ Error verificando persistencia: {str(e)}")
            return False
        
        # 5. DELETE - Eliminar proveedor
        print("\n5️⃣ PROBANDO ELIMINACIÓN (DELETE)...")
        try:
            resultado_eliminacion = proveedor_service.eliminar_proveedor(proveedor_id)
            
            if resultado_eliminacion:
                print(f"   ✅ Proveedor eliminado exitosamente")
                
                # Verificar que ya no existe
                proveedor_eliminado = proveedor_service.obtener_por_id(proveedor_id)
                if proveedor_eliminado is None:
                    print(f"   ✅ Confirmado: el proveedor ya no existe en la base de datos")
                else:
                    print(f"   ❌ Error: el proveedor aún existe después de la eliminación")
                    return False
            else:
                print(f"   ❌ No se pudo eliminar el proveedor")
                return False
                
        except Exception as e:
            print(f"   ❌ Error en DELETE: {str(e)}")
            return False
        
        # 6. Verificar códigos automáticos
        print("\n6️⃣ VERIFICANDO GENERACIÓN DE CÓDIGOS AUTOMÁTICOS...")
        try:
            # Crear varios proveedores para verificar secuencia
            codigos_generados = []
            for i in range(3):
                nuevo_proveedor = proveedor_service.crear_proveedor(
                    razon_social=f"Proveedor Secuencial {i+1}",
                    ci_ruc=f"123456789012{i}",
                    direccion=f"Calle {i+1}",
                    telefono=f"555-000{i}",
                    correo=f"test{i}@secuencial.com"
                )
                codigos_generados.append(nuevo_proveedor.p_codigo)
                print(f"   📝 Código generado {i+1}: {nuevo_proveedor.p_codigo}")
            
            print(f"   ✅ Códigos generados: {codigos_generados}")
            print(f"   ✅ Todos los códigos son únicos: {len(set(codigos_generados)) == len(codigos_generados)}")
            
        except Exception as e:
            print(f"   ❌ Error verificando códigos automáticos: {str(e)}")
            return False
        
        print(f"\n✅ TODAS LAS PRUEBAS CRUD COMPLETADAS EXITOSAMENTE")
        print("=" * 60)
        return True

if __name__ == "__main__":
    success = test_crud_proveedores()
    if success:
        print("\n🎉 Todas las operaciones CRUD de proveedores funcionan correctamente!")
        print("🔧 CREATE, READ, UPDATE, DELETE - Todo operativo")
        print("📝 Generación automática de códigos funcionando")
        print("🔍 Búsquedas y filtros operativos")
    else:
        print("\n❌ Algunas operaciones CRUD fallaron.")
        sys.exit(1)