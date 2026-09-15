# Reglas y pesos

## Transacciones

| Regla | Peso | Justificación |
|---|---:|---|
| Beneficiario y dispositivo nuevos | 0,35 | La coincidencia sugiere toma de cuenta. |
| Beneficiario nuevo | 0,35 | Justifica autenticación adicional sin bloquear por sí sola. |
| Monto mayor a 3× promedio | 0,30 | Desviación material del patrón del cliente. |
| Más de 5 transacciones/hora | 0,50 | Señal fuerte de automatización o fraccionamiento en el set sintético. |
| 3 o más accesos fallidos | 0,25 | Señal de credenciales comprometidas. |
| País IP distinto | 0,30 | Anomalía geográfica verificable. |
| VPN y monto alto | 0,25 | Eleva el riesgo cuando se combina con exposición. |
| Sesión menor a 20 segundos | 0,15 | Señal débil; nunca bloquea sola. |
| Cuenta menor a 30 días | 0,20 | Señal de cuenta nueva o mula. |
| Beneficiario nuevo y monto ≥ 2× | 0,25 | Combinación específica que eleva exposición sin depender de identidad. |
| Horario nocturno y distancia ≥ 100 km | 0,30 | Conjunción de dos anomalías; una sola no basta. |

El fuzzy pondera monto relativo (45 %), velocidad (35 %) y distancia (20 %). El score final usa 45 % reglas/fuzzy, 25 % similitud y 30 % razonamiento estructurado.

## Documentos

Los checks de RUT, fechas y aritmética son críticos. Un fallo crítico impide `autentico` aunque el score quede bajo el umbral de revisión. Metadatos de editor generan `warn`, no un veredicto `falso` por sí solos.
