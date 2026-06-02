
#
#   Archivo:    2_ai_module.py
#   Fecha:      01/Junio/2026
#   Autor:      Gabriel Alberto Brito Campos.
#
#   Proyecto:   MELI. CapEx. Service Center Tracker
#   Objetivo:   Generar resumen ejecutivo de riesgos usando Claude API.
#

##############################
### IMPORTS
import anthropic
import os
import pandas as pd
import json
import gspread
from google.oauth2.service_account import Credentials

##############################
### CONFIGURACION

# API Key de Anthropic  // API Especifica para este proyecto.
ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY')

# Campos relevantes para el analisis de riesgo y accionables. // Recomendacion.
CAMPOS_RIESGO = [
    'id_sc', 'nombre_sc', 'estado', 'estatus_general',
    'dias_retraso', 'avance_obra_civil_pct', 'avance_compras_pct',
    'avance_licencias_pct', 'avance_ponderado_pct',
    'capex_presupuestado_usd', 'capex_ejercido_usd',
    'capex_burn_rate_pct', 'avance_vs_gasto',
    'sobre_presupuesto', 'fecha_estimada_apertura', 'observaciones'
]


##############################
### CONEXION GOOGLE SHEETS

SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]

creds = Credentials.from_service_account_file('credentials.json', scopes=SCOPES)
gc = gspread.authorize(creds)

# Leer datos procesados desde hoja de output
sh_destino = gc.open('SetUp - Capex - Progress')
hoja_datos = sh_destino.worksheet('Datos Consolidados')
datos = hoja_datos.get_all_records()
df_sc = pd.DataFrame(datos)

print(f"Datos cargados: {df_sc.shape[0]} Service Centers")


##############################
### FUNCION PRINCIPAL

def generar_resumen(df: pd.DataFrame) -> str:

    # Filtrar solo campos relevantes
    df_riesgo = df[CAMPOS_RIESGO].copy()
    df_json = df_riesgo.to_json(orient='records', force_ascii=False, indent=2)

    prompt = f"""
Eres analista senior del equipo de Set Up de Mercado Libre México.
Tu función es preparar el reporte semanal de seguimiento de aperturas de Service Centers.

Este reporte lo lee el equipo de Set Up cada lunes para priorizar su semana.

INSTRUCCIONES:
1. Escribe UN párrafo de resumen ejecutivo (máximo 80 palabras) con el estado general de las aperturas esta semana.
2. Identifica los 3 principales puntos de atención que el equipo debe resolver esta semana, ordenados de mayor a menor urgencia.
3. Para cada punto de atención propone UNA acción concreta que incluya:
   - Qué hacer exactamente (usa verbos concretos: escalar, contactar, renegociar, pausar, auditar)
   - A quién le corresponde dentro del equipo de Set Up (Gerente de Obra, Compras, Legal, Dirección)
   - En qué plazo (en 24 horas, antes del viernes, esta semana)
4. Menciona brevemente qué SCs están avanzando bien y no requieren atención inmediata.
5. Genera una tabla de clasificación de riesgo por SC con este formato exacto, una línea por SC:

SEMAFORO | id_sc | justificacion breve

Usa SOLO estas categorías:
- ROJO: retraso crítico >14 días, sobre presupuesto, o riesgo grave en observaciones
- AMARILLO: retraso entre 7-14 días, avance_vs_gasto negativo, o riesgo identificado en observaciones
- VERDE: sin retrasos, avance normal, sin alertas en observaciones

IMPORTANTE: Las observaciones contienen contexto operativo crítico.
-Un SC con dias_retraso=0 puede ser AMARILLO si sus observaciones indican un riesgo inminente.
-Analiza en profundidad pero escribe de forma concisa. 
-Cada sección debe ser escaneable en 10 segundos. 
-Sin explicaciones largas — solo hechos y acciones.


CRITERIOS DE RIESGO A CONSIDERAR:
- SCs con dias_retraso > 14 son críticos — ROJO
- SCs con dias_retraso entre 7 y 14 — AMARILLO
- SCs con avance_vs_gasto negativo están gastando más de lo que avanzan
- SCs con sobre_presupuesto = True requieren atención financiera


DATOS DEL REPORTE SEMANAL:
{df_json}

FORMATO DE RESPUESTA:
## Resumen Ejecutivo
[párrafo aquí]

## Puntos de Atención Esta Semana
**1. [SC-XXX — descripción del problema]**
Acción: [quién hace qué en qué plazo]

**2. [SC-XXX — descripción del probl
"""

    # Llamada a Claude API
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    msg = client.messages.create(
        model='claude-sonnet-4-6',
        max_tokens=1500,
        messages=[{'role': 'user', 'content': prompt}]
    )
    return msg.content[0].text


##############################
### EJECUTAR Y EXPORTAR

# Generar resumen
print("\nGenerando resumen ejecutivo con Claude...")
resumen = generar_resumen(df_sc)

# Mostrar en terminal
print("\n" + "="*60)
print(resumen)
print("="*60)

# Exportar resumen a tercera hoja en Google Sheets
try:
    hoja_ai = sh_destino.worksheet('Resumen IA')
    hoja_ai.clear()
except:
    hoja_ai = sh_destino.add_worksheet(title='Resumen IA', rows=50, cols=5)

# Escribir resumen como texto en la hoja
hoja_ai.update('A1', [['Resumen Ejecutivo IA'], [resumen]])
print("\nExportacion exitosa — Hoja 3: Resumen IA")        