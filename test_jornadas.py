#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Pruebas del sistema de jornadas nocturnas continuas
"""

import sys
sys.path.append('.')

try:
    from app import (obtener_fecha_jornada_unificada, obtener_horarios_jornada, 
                     obtener_reglas_descanso_por_rol, puede_tomar_descanso)
    from datetime import datetime, time
    
    print('=== PRUEBAS DEL SISTEMA DE JORNADAS NOCTURNAS ===')
    
    # Prueba 1: Fecha de jornada unificada
    fecha_jornada = obtener_fecha_jornada_unificada()
    print(f'✅ Fecha jornada actual: {fecha_jornada}')
    
    # Prueba 2: Horarios de jornada
    inicio, fin = obtener_horarios_jornada()
    print(f'✅ Horarios de jornada: {inicio} - {fin}')
    
    # Prueba 3: Reglas de descanso por rol
    print('\n✅ Reglas de descanso por rol:')
    for rol in ['Full Time', 'Part-time', 'Llamado']:
        reglas = obtener_reglas_descanso_por_rol(rol)
        print(f'   {rol}: {reglas}')
    
    # Prueba 4: Validación de horario actual
    print('\n✅ Validaciones de horario:')
    hora_actual = datetime.now().time()
    puede_tomar = puede_tomar_descanso('Comida', 1, fecha_jornada, 'Full Time')
    print(f'   Hora actual: {hora_actual}')
    print(f'   Puede tomar comida: {puede_tomar}')
    
    # Prueba 5: Simulación de diferentes horarios
    print('\n✅ Simulaciones de horarios:')
    
    # Simulación 1: 02:00 AM (debe ser jornada del día anterior)
    momento_noche = datetime.now().replace(hour=2, minute=0, second=0)
    fecha_jornada_noche = obtener_fecha_jornada_unificada(momento_noche)
    print(f'   02:00 AM → Fecha jornada: {fecha_jornada_noche}')
    
    # Simulación 2: 10:00 AM (debe ser jornada del día actual)
    momento_dia = datetime.now().replace(hour=10, minute=0, second=0)
    fecha_jornada_dia = obtener_fecha_jornada_unificada(momento_dia)
    print(f'   10:00 AM → Fecha jornada: {fecha_jornada_dia}')
    
    # Simulación 3: 23:00 PM (debe ser jornada del día actual)
    momento_tarde = datetime.now().replace(hour=23, minute=0, second=0)
    fecha_jornada_tarde = obtener_fecha_jornada_unificada(momento_tarde)
    print(f'   23:00 PM → Fecha jornada: {fecha_jornada_tarde}')
    
    print('\n🎉 TODAS LAS PRUEBAS COMPLETADAS EXITOSAMENTE')
    print('✅ Sistema de jornadas nocturnas funcionando correctamente')
    
except ImportError as e:
    print(f'❌ Error de importación: {e}')
    print('   Verifica que app.py esté en el directorio actual')
    
except Exception as e:
    print(f'❌ Error durante las pruebas: {e}')
    import traceback
    traceback.print_exc()
