# MELI SetUp - CapEx Service Center Progress

## Descripción
Pipeline automatizado de seguimiento semanal de avances y progreso de Service Centers.
Consolida datos, aplica validaciones de calidad, calcula métricas operativas
y genera un resumen ejecutivo con IA para el equipo de Set Up.

## Arquitectura
Google Sheets (source) > ETL Python > Google Sheets (output) --> Dashboard Tableau  
                                                             --> Claude API -> Resumen Ejecutivo 


## Entregables
`1_etl.py` — Pipeline ETL con capa de Data Quality y métricas
`2_ai_module.py` — Módulo de IA para detección de riesgos con Claude API
`Dashboard - SetUp - CapEx Progress.twb` - Dashboard basico de presentacion.

## Requisitos
## Configuración
1. Agrega tu archivo `credentials.json` de Google Cloud en la carpeta raíz
2. Define tu API key de Anthropic como variable de entorno: $env:ANTHROPIC_API_KEY = "tu-key"
3. Correr ETL: python 1_etl.py
4. Correr modulo IA: 2_ai_module.py

## Dashboard
El dashboard se construyó en Tableau Desktop.
- Fuente de datos: Google Sheets `SetUp - Capex - Progress` → pestaña `Datos Consolidados`
- Para actualizar el dashboard:
  1. En Google Sheets: File → Download → Excel (.xlsx)
  2. Reemplazar el archivo en la carpeta `data/`
  3. Abrir el workbook en Tableau Desktop y hacer Refresh de la fuente
  4. Republicar en Tableau Public
- Link público: (pendiente: validar si por privacidad se puede)

## Data Quality
La capa de DQ valida 3 niveles:
- **Técnico** — nulos en campos obligatorios
- **Referencial** — rangos imposibles y valores fuera de catálogo
- **Negocio** — inconsistencias operativas entre campos

Los warnings se exportan automáticamente a la pestaña `Data Quality` en Google Sheets.

## Métricas Calculadas
| Métrica | Descripción | Nota
|---------|-------------|
| `avance_ponderado_pct` | Avance consolidado ponderado por etapa | Ponderacion de Avances: 40% Obra Civil, 30% Compras, 30% Permisos
| `capex_burn_rate_pct` | % del presupuesto ya ejercido |
| `avance_vs_gasto` | Diferencia entre avance y gasto — positivo es eficiente |
| `sobre_presupuesto` | Flag cuando capex ejercido supera el presupuestado |
| `eficiencia_throughput_pct` | % de capacidad operativa utilizada |

## Autor
Gabriel Alberto Brito Campos




