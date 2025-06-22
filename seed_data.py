#!/usr/bin/env python3
"""
Script para poblar la base de datos con datos de prueba
"""

import sys
from os.path import abspath, dirname
from datetime import datetime, date, time

# Añade el directorio del proyecto al PYTHONPATH
sys.path.insert(0, dirname(abspath(__file__)))

from app import create_app
from app.database import db
from app.database.models import (
    Usuario, Persona, Proveedor, Item, Instrumento, Articulo, 
    Stock, Consumo, Entrada, MovimientoDetalle
)

def create_sample_data():
    """Crea datos de prueba para el sistema"""
    
    # Crear usuario de prueba
    usuario = Usuario(
        u_username='admin',
        u_password='admin123'  # En producción debería estar hasheado
    )
    usuario.save()
    print("✓ Usuario creado")

    # Crear personas
    personas = [
        Persona(pe_codigo='P001', pe_nombre='Juan Pérez'),
        Persona(pe_codigo='P002', pe_nombre='María García'),
        Persona(pe_codigo='P003', pe_nombre='Carlos López')
    ]
    
    for persona in personas:
        persona.save()
    print("✓ Personas creadas")

    # Crear proveedores
    proveedores_data = [
        {
            'p_codigo': 'PROV001',
            'p_razonsocial': 'Instrumentos Musicales S.A.',
            'p_ci_ruc': '1234567890123',
            'p_direccion': 'Av. Principal 123, Quito',
            'p_telefono': '0987654321',
            'p_correo': 'ventas@instrumentos.com'
        },
        {
            'p_codigo': 'PROV002', 
            'p_razonsocial': 'Suministros Educativos Ltda.',
            'p_ci_ruc': '9876543210987',
            'p_direccion': 'Calle Secundaria 456, Guayaquil',
            'p_telefono': '0912345678',
            'p_correo': 'info@suministros.com'
        },
        {
            'p_codigo': 'PROV003',
            'p_razonsocial': 'Papelería Central',
            'p_ci_ruc': '5555555555555',
            'p_direccion': 'Centro Comercial Plaza, Local 15',
            'p_telefono': '0999888777',
            'p_correo': 'pedidos@papeleria.com'
        }
    ]
    
    proveedores = []
    for prov_data in proveedores_data:
        proveedor = Proveedor(**prov_data)
        proveedor.save()
        proveedores.append(proveedor)
    print("✓ Proveedores creados")

    # Crear instrumentos
    instrumentos_data = [
        {
            'item': {
                'i_codigo': 'INST001',
                'i_nombre': 'Violín 4/4 Profesional',
                'i_tipo': 'instrumento',
                'i_cantidad': 1,
                'i_vUnitario': 450.00,
                'i_vTotal': 450.00
            },
            'instrumento': {
                'i_marca': 'Yamaha',
                'i_modelo': 'V7SG',
                'i_serie': 'YV001234',
                'i_estado': 'Disponible'
            }
        },
        {
            'item': {
                'i_codigo': 'INST002',
                'i_nombre': 'Piano Digital 88 Teclas',
                'i_tipo': 'instrumento',
                'i_cantidad': 1,
                'i_vUnitario': 1200.00,
                'i_vTotal': 1200.00
            },
            'instrumento': {
                'i_marca': 'Casio',
                'i_modelo': 'CDP-S110',
                'i_serie': 'CS987654',
                'i_estado': 'Disponible'
            }
        },
        {
            'item': {
                'i_codigo': 'INST003',
                'i_nombre': 'Guitarra Acústica',
                'i_tipo': 'instrumento',
                'i_cantidad': 1,
                'i_vUnitario': 280.00,
                'i_vTotal': 280.00
            },
            'instrumento': {
                'i_marca': 'Fender',
                'i_modelo': 'CD-60S',
                'i_serie': 'FG456789',
                'i_estado': 'En uso'
            }
        }
    ]
    
    for inst_data in instrumentos_data:
        # Crear item
        item = Item(**inst_data['item'])
        item.save()
        
        # Crear instrumento
        inst_data['instrumento']['i_id'] = item.id
        instrumento = Instrumento(**inst_data['instrumento'])
        instrumento.save()
        
        # Crear stock
        stock = Stock(s_cantidad=1, i_id=item.id)
        stock.save()
    
    print("✓ Instrumentos creados")

    # Crear artículos
    articulos_data = [
        {
            'item': {
                'i_codigo': 'ART001',
                'i_nombre': 'Cuerdas para Violín (Juego)',
                'i_tipo': 'articulo',
                'i_cantidad': 25,
                'i_vUnitario': 15.50,
                'i_vTotal': 387.50
            },
            'articulo': {
                'a_c_contable': '5101001',
                'a_stockMin': 10,
                'a_stockMax': 50
            }
        },
        {
            'item': {
                'i_codigo': 'ART002',
                'i_nombre': 'Partituras Impresas',
                'i_tipo': 'articulo',
                'i_cantidad': 5,  # Stock bajo para prueba
                'i_vUnitario': 2.50,
                'i_vTotal': 12.50
            },
            'articulo': {
                'a_c_contable': '5101002',
                'a_stockMin': 20,
                'a_stockMax': 100
            }
        },
        {
            'item': {
                'i_codigo': 'ART003',
                'i_nombre': 'Atriles para Partitura',
                'i_tipo': 'articulo',
                'i_cantidad': 15,
                'i_vUnitario': 35.00,
                'i_vTotal': 525.00
            },
            'articulo': {
                'a_c_contable': '5101003',
                'a_stockMin': 5,
                'a_stockMax': 30
            }
        },
        {
            'item': {
                'i_codigo': 'ART004',
                'i_nombre': 'Resina para Arco',
                'i_tipo': 'articulo',
                'i_cantidad': 3,  # Stock crítico
                'i_vUnitario': 8.75,
                'i_vTotal': 26.25
            },
            'articulo': {
                'a_c_contable': '5101004',
                'a_stockMin': 15,
                'a_stockMax': 40
            }
        },
        {
            'item': {
                'i_codigo': 'ART005',
                'i_nombre': 'Metrónomo Digital',
                'i_tipo': 'articulo',
                'i_cantidad': 8,
                'i_vUnitario': 45.00,
                'i_vTotal': 360.00
            },
            'articulo': {
                'a_c_contable': '5101005',
                'a_stockMin': 3,
                'a_stockMax': 15
            }
        }
    ]
    
    for art_data in articulos_data:
        # Crear item
        item = Item(**art_data['item'])
        item.save()
        
        # Crear artículo
        art_data['articulo']['i_id'] = item.id
        articulo = Articulo(**art_data['articulo'])
        articulo.save()
        
        # Crear stock
        stock = Stock(s_cantidad=item.i_cantidad, i_id=item.id)
        stock.save()
    
    print("✓ Artículos creados")

    # Crear algunas entradas
    entrada1 = Entrada(
        e_fecha=date.today(),
        e_hora=time(10, 30),
        e_descripcion='Compra inicial de suministros',
        e_numFactura='FAC-001-2024',
        p_id=proveedores[0].id
    )
    entrada1.save()

    entrada2 = Entrada(
        e_fecha=date.today(),
        e_hora=time(14, 15),
        e_descripcion='Reposición de partituras',
        e_numFactura='FAC-002-2024',
        p_id=proveedores[1].id
    )
    entrada2.save()
    
    print("✓ Entradas creadas")

    # Crear algunos movimientos de ejemplo
    # Obtener algunos items para crear movimientos
    items = Item.query.filter_by(i_tipo='articulo').limit(3).all()
    
    for i, item in enumerate(items):
        # Movimiento de entrada
        movimiento_entrada = MovimientoDetalle(
            m_fecha=date.today(),
            m_tipo='entrada',
            m_cantidad=10,
            m_valorUnitario=item.i_vUnitario,
            m_valorTotal=10 * item.i_vUnitario,
            m_observaciones=f'Entrada inicial de {item.i_nombre}',
            i_id=item.id,
            e_id=entrada1.id if i == 0 else entrada2.id,
            u_id=usuario.id
        )
        movimiento_entrada.save()
        
        # Movimiento de salida (solo para algunos)
        if i < 2:
            movimiento_salida = MovimientoDetalle(
                m_fecha=date.today(),
                m_tipo='salida',
                m_cantidad=3,
                m_valorUnitario=item.i_vUnitario,
                m_valorTotal=3 * item.i_vUnitario,
                m_observaciones=f'Consumo de {item.i_nombre}',
                i_id=item.id,
                u_id=usuario.id
            )
            movimiento_salida.save()
    
    print("✓ Movimientos creados")
    print("\n🎉 Datos de prueba creados exitosamente!")
    print("\nDatos creados:")
    print(f"- 1 Usuario (admin/admin123)")
    print(f"- 3 Personas")
    print(f"- 3 Proveedores")
    print(f"- 3 Instrumentos")
    print(f"- 5 Artículos (algunos con stock bajo)")
    print(f"- 2 Entradas")
    print(f"- Varios movimientos de prueba")

def main():
    """Función principal"""
    app = create_app()
    
    with app.app_context():
        print("🚀 Iniciando creación de datos de prueba...")
        
        # Verificar si ya existen datos
        if Usuario.query.first():
            print("⚠️  Ya existen datos en la base de datos.")
            respuesta = input("¿Desea continuar y agregar más datos? (s/N): ")
            if respuesta.lower() != 's':
                print("❌ Operación cancelada.")
                return
        
        try:
            create_sample_data()
        except Exception as e:
            print(f"❌ Error al crear datos: {e}")
            db.session.rollback()
        else:
            print("\n✅ Proceso completado exitosamente!")

if __name__ == '__main__':
    main()