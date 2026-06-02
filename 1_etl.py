
#
#   Archivo:    1_etl.py
#   Fecha:      31/Mayo/2026
#   Autor:      Gabriel Alberto Brito Campos.
#   
#   Proyecto:   MELI. CapEx. Service Center Tracker  
#   Objetivo:   
#  
#               Leer archivo fuente,
#               Aplicar Data Quality,
#               Calculo Metricas,
#               Exportar.
#

##############################
### IMPORTS
import pandas as pd
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials


##############################
### FUNCTIONS

# division_segura
# Si denominador es 0 o nulo — regresa 0 directo
def division_segura(numerador, denominador, redondeo=2):
    if pd.isna(numerador) or pd.isna(denominador):
        return 0
    if denominador == 0:
        return 0
    return round(numerador / denominador, redondeo)

# log_warnings

# Lista que acumula todos los warnings detectados
dq_warnings = []

# Para registrar warnings de calidad de datos
def log_warning(id_sc, campo, problema, severidad, categoria):
    dq_warnings.append({
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M'),
        'id_sc': id_sc,
        'campo': campo,
        'problema': problema,
        'severidad': severidad,
        'categoria': categoria
    })






##############################
### Conexion Google Sheets ###

SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]

creds = Credentials.from_service_account_file('credentials.json', scopes=SCOPES)
gc = gspread.authorize(creds)

# Sheet fuente — 
sh_fuente = gc.open('Caso práctico Service centers')

# Sheet destino — donde escribimos el output procesado
sh_destino = gc.open('SetUp - Capex - Progress')

print(f"Conexion exitosa — Fuente: {sh_fuente.title}")
print(f"Conexion exitosa — Destino: {sh_destino.title}")


##############################
### 1. Carga/Lectura de Archivo.

# Leer desde Google Sheets fuente
hoja_fuente = sh_fuente.worksheet('service_centers_dataset.csv')
datos = hoja_fuente.get_all_records()
df_sc = pd.DataFrame(datos)

print(f"Shape: {df_sc.shape}")
print("\nColumnas:")
print(df_sc.columns.tolist())
print(df_sc.iloc[0])


##############################
### 2. Calidad de Datos ###

# Función para registrar warnings
# Severidad: Alta / Media / Baja
# Categoria: Nulo / Inconsistencia / Fuera de rango / Negocio

# Campos que NO deben ser nulos - severidad Alta
campos_alta = ['id_sc']

# Campos que NO deben ser nulos - severidad Media
campos_media = [
    'nombre_sc',
    'estado', 
    'tipo_sc',
    'fecha_estimada_apertura',
    'capex_presupuestado_usd',
    'capex_ejercido_usd',
    'estatus_general'
]

# Validar nulos por fila
for _, row in df_sc.iterrows():
    
    # Validar campos Alta severidad
    for campo in campos_alta:
        if pd.isna(row[campo]) or str(row[campo]).strip() == '':
            log_warning(
                id_sc=row['id_sc'],
                campo=campo,
                problema=f"Campo obligatorio '{campo}' esta nulo o vacio",
                severidad='Alta',
                categoria='Nulo'
            )
    
    # Validar campos Media severidad
    for campo in campos_media:
        if pd.isna(row[campo]) or str(row[campo]).strip() == '':
            log_warning(
                id_sc=row['id_sc'],
                campo=campo,
                problema=f"Campo obligatorio '{campo}' esta nulo o vacio",
                severidad='Media',
                categoria='Nulo'
            )


# -----------------------------------------------
# Validaciones de Inconsistencia entre campos

for _, row in df_sc.iterrows():

    # SC Operativo sin fecha de apertura real
    if row['estatus_general'] == 'Operativo' and pd.isna(row['fecha_apertura_real']):
        log_warning(
            id_sc=row['id_sc'],
            campo='fecha_apertura_real',
            problema='SC con estatus Operativo no tiene fecha de apertura real registrada',
            severidad='Alta',
            categoria='Inconsistencia'
        )

    # Capex ejercido mayor al presupuestado
    if not pd.isna(row['capex_ejercido_usd']) and not pd.isna(row['capex_presupuestado_usd']):
        if row['capex_ejercido_usd'] > row['capex_presupuestado_usd']:
            log_warning(
                id_sc=row['id_sc'],
                campo='capex_ejercido_usd',
                problema=f"Capex ejercido ({row['capex_ejercido_usd']}) supera el presupuestado ({row['capex_presupuestado_usd']})",
                severidad='Alta',
                categoria='Negocio'
            )

    # Dias de retraso = 0 pero fecha estimada ya paso
    if not pd.isna(row['fecha_estimada_apertura']):
        fecha_estimada = pd.to_datetime(row['fecha_estimada_apertura'])
        if fecha_estimada < pd.to_datetime('today') and row['dias_retraso'] == 0 and row['estatus_general'] != 'Operativo':
            log_warning(
                id_sc=row['id_sc'],
                campo='dias_retraso',
                problema='Fecha estimada ya vencio pero dias_retraso reporta cero y SC no esta operativo',
                severidad='Media',
                categoria='Inconsistencia'
            )

    # Throughput real > 0 pero SC no esta operativo
    if row['throughput_real_ult_semana'] > 0 and row['estatus_general'] != 'Operativo' and row['estatus_general'] != 'En operación piloto':
        log_warning(
            id_sc=row['id_sc'],
            campo='throughput_real_ult_semana',
            problema='SC reporta throughput real pero no tiene estatus operativo',
            severidad='Media',
            categoria='Inconsistencia'
        )


# -----------------------------------------------
# Validaciones Referenciales - Rangos y Catalogos

# Catalogos de valores validos
cat_nivel_automatizacion = ['manual', 'semi', 'full']
cat_estatus_general = ['En obra civil', 'En habilitación', 'Pre-apertura', 'En operación piloto', 'Operativo']
cat_tipo_sc = ['Pequeño', 'Mediano', 'Grande', 'Especializado']

for _, row in df_sc.iterrows():

    # Valores negativos o imposibles - Severidad Alta
    if not pd.isna(row['capex_presupuestado_usd']) and row['capex_presupuestado_usd'] <= 0:
        log_warning(
            id_sc=row['id_sc'],
            campo='capex_presupuestado_usd',
            problema=f"Valor imposible: {row['capex_presupuestado_usd']} — debe ser mayor a 0",
            severidad='Alta',
            categoria='Fuera de rango'
        )

    if not pd.isna(row['capex_ejercido_usd']) and row['capex_ejercido_usd'] < 0:
        log_warning(
            id_sc=row['id_sc'],
            campo='capex_ejercido_usd',
            problema=f"Valor imposible: {row['capex_ejercido_usd']} — no puede ser negativo",
            severidad='Alta',
            categoria='Fuera de rango'
        )

    if not pd.isna(row['m2_operativos']) and row['m2_operativos'] <= 0:
        log_warning(
            id_sc=row['id_sc'],
            campo='m2_operativos',
            problema=f"Valor imposible: {row['m2_operativos']} — debe ser mayor a 0",
            severidad='Alta',
            categoria='Fuera de rango'
        )

    if not pd.isna(row['throughput_diario_meta']) and row['throughput_diario_meta'] <= 0:
        log_warning(
            id_sc=row['id_sc'],
            campo='throughput_diario_meta',
            problema=f"Valor imposible: {row['throughput_diario_meta']} — debe ser mayor a 0",
            severidad='Alta',
            categoria='Fuera de rango'
        )

    if not pd.isna(row['dias_retraso']) and row['dias_retraso'] < 0:
        log_warning(
            id_sc=row['id_sc'],
            campo='dias_retraso',
            problema=f"Valor imposible: {row['dias_retraso']} — no puede ser negativo",
            severidad='Alta',
            categoria='Fuera de rango'
        )

    # Catalogos - Severidad Media
    if not pd.isna(row['nivel_automatizacion']) and row['nivel_automatizacion'] not in cat_nivel_automatizacion:
        log_warning(
            id_sc=row['id_sc'],
            campo='nivel_automatizacion',
            problema=f"Valor fuera de catalogo: '{row['nivel_automatizacion']}' — valores validos: {cat_nivel_automatizacion}",
            severidad='Media',
            categoria='Fuera de rango'
        )

    if not pd.isna(row['estatus_general']) and row['estatus_general'] not in cat_estatus_general:
        log_warning(
            id_sc=row['id_sc'],
            campo='estatus_general',
            problema=f"Valor fuera de catalogo: '{row['estatus_general']}' — valores validos: {cat_estatus_general}",
            severidad='Media',
            categoria='Fuera de rango'
        )

    if not pd.isna(row['tipo_sc']) and row['tipo_sc'] not in cat_tipo_sc:
        log_warning(
            id_sc=row['id_sc'],
            campo='tipo_sc',
            problema=f"Valor fuera de catalogo: '{row['tipo_sc']}' — valores validos: {cat_tipo_sc}",
            severidad='Media',
            categoria='Fuera de rango'
        )


# -----------------------------------------------
# Topado de porcentajes — registrar warning y corregir
# Esta paso de DQ si ajusta los valores de porcentaje para estar en un rango de 0 a 100.

campos_pct = ['avance_obra_civil_pct', 'avance_compras_pct', 'avance_licencias_pct',
              'mix_gm_pct', 'mix_large_pct', 'mix_oversize_pct']

for _, row in df_sc.iterrows():
    for campo in campos_pct:
        if not pd.isna(row[campo]):
            if row[campo] < 0:
                log_warning(row['id_sc'], campo,
                    f"Porcentaje {row[campo]} < 0 — corregido a 0",
                    'Alta', 'Fuera de rango')
            elif row[campo] > 100:
                log_warning(row['id_sc'], campo,
                    f"Porcentaje {row[campo]} > 100 — topado a 100",
                    'Alta', 'Fuera de rango')

# Aplicar correccion despues de registrar
for campo in campos_pct:
    df_sc[campo] = df_sc[campo].clip(lower=0, upper=100)



# Mostrar resumen de warnings
df_dq = pd.DataFrame(dq_warnings)

if len(dq_warnings) == 0:
    print("\nData Quality: Sin warnings detectados.")
else:
    print(f"\nData Quality: {len(dq_warnings)} warnings detectados.")
    print(df_dq)

 

##############################
### 3. Calculo de Metricas ###

# Eficiencia de throughput — que tan cerca esta el SC de su capacidad maxima
df_sc['eficiencia_throughput_pct'] = df_sc.apply(
    lambda row: division_segura(row['throughput_real_ult_semana'], row['throughput_diario_meta']) * 100,
    axis=1
)

# Avance ponderado —  
df_sc['avance_ponderado_pct'] = (
    df_sc['avance_obra_civil_pct'] * 0.40 +
    df_sc['avance_compras_pct']    * 0.30 +
    df_sc['avance_licencias_pct']  * 0.30
).round(2)


# Capex burn rate
df_sc['capex_burn_rate_pct'] = df_sc.apply(
    lambda row: division_segura(row['capex_ejercido_usd'], row['capex_presupuestado_usd']) * 100,
    axis=1
)

# Diferencia entre avance y gasto — positivo es bueno, negativo es riesgo
df_sc['avance_vs_gasto'] = (
    df_sc['avance_ponderado_pct'] - df_sc['capex_burn_rate_pct']
).round(2)


# Flag sobre presupuesto — True si capex ejercido supera el presupuestado
df_sc['sobre_presupuesto'] = df_sc['capex_ejercido_usd'] > df_sc['capex_presupuestado_usd']


# Mostrar resultado de metricas
print("\nMetricas calculadas:")
print(df_sc[['id_sc', 'avance_ponderado_pct', 'capex_burn_rate_pct',
             'avance_vs_gasto', 'sobre_presupuesto',
             'eficiencia_throughput_pct']].to_string())


##############################
### 4. Exportar ###

# Hoja 1 - Datos Procesados
# Hoja 2 - Reporte de Warnings de Calidad de Datos


# Preparar hoja 1 — DataFrame consolidado con metricas
# Convertir NaN a cadena vacia para que Google Sheets lo acepte
df_export = df_sc.copy()
df_export = df_export.fillna('')
df_export['sobre_presupuesto'] = df_export['sobre_presupuesto'].astype(str)

# Abrir hoja 1 — datos principales
hoja_datos = sh_destino.sheet1
hoja_datos.clear()
hoja_datos.update(
    [df_export.columns.values.tolist()] + df_export.values.tolist()
)
hoja_datos.update_title('Datos Consolidados')
print("\nExportacion exitosa — Hoja 1: Datos Consolidados")

# Preparar hoja 2 — reporte de Data Quality
if len(dq_warnings) > 0:
    df_dq_export = df_dq.fillna('')
    
    # Crear segunda hoja si no existe
    try:
        hoja_dq = sh_destino.worksheet('Data Quality')
        hoja_dq.clear()
    except:
        hoja_dq = sh_destino.add_worksheet(title='Data Quality', rows=100, cols=10)
    
    hoja_dq.update(
        [df_dq_export.columns.values.tolist()] + df_dq_export.values.tolist()
    )
    print(f"Exportacion exitosa — Hoja 2: Data Quality ({len(dq_warnings)} warnings)")
else:
    print("Data Quality: Sin warnings — hoja 2 no generada")

print("\nProceso completado exitosamente.")

##############################