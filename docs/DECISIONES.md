# Decisiones técnicas

- ADR-001: SQLite y embeddings JSON para el MVP; `VectorStore` queda desacoplado para migrar a pgvector.
- ADR-002: modo mock determinista por defecto para demos y tests sin consumo.
- ADR-003: revisión humana obligatoria en bloqueos, documentos sospechosos o falsos.
- ADR-004: máximo dos envíos visuales por documento; extracción y análisis forense.
- ADR-005: el Excel entregado es la fuente reproducible de evaluación y no contiene datos reales.
- ADR-006: los documentos procesados se guardan solo bajo `data/traces/{trace_id}` y expiran según configuración.
- ADR-007: las respuestas OpenAI usan `store=false`; los precios configurables se actualizaron a la documentación oficial consultada el 14-09-2026 (Luna: USD 0,20 input / 1,20 output por MTok).
