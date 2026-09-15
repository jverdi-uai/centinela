# Evaluación de documentos

Modo: `mock` · Casos: 12

| Métrica | Resultado |
|---|---:|
| Exactitud operativa | 1.000 |
| Recall de documentos alterados | 1.000 |
| Latencia p50 | 24.39 ms |
| Latencia p95 | 26.74 ms |
| Costo por documento | USD 0.00000000 |

Checks fallidos más frecuentes: {'consistencia_fechas': 1, 'rut_modulo_11': 1, 'consistencia_montos': 1}.

La comparación entre modelos queda disponible al ejecutar dos veces con `OPENAI_VISION_MODEL`; no se consume API en la evaluación mock.
