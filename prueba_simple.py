#!/usr/bin/env python3
"""Prueba simple del sistema de jornadas"""
import sys
import os

# Agregar el directorio actual al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    print("=== PRUEBA DEL SISTEMA DE JORNADAS NOCTURNAS ===")
    
    # Importar funciones
    from app import obtener_fecha_jornada_unificada, obtener_horarios_jornada
    print("✅ Funciones importadas correctamente")
    
    # Prueba básica
    fecha_jornada = obtener_fecha_jornada_unificada()
    print(f"✅ Fecha de jornada unificada: {fecha_jornada}")
    
    horarios = obtener_horarios_jornada()
    print(f"✅ Horarios de jornada: {horarios}")
    
    print("\n🎉 SISTEMA FUNCIONANDO CORRECTAMENTE")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
