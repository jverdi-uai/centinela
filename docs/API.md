# API Centinela

Base local: `http://127.0.0.1:8000/api/v1`. La documentación interactiva queda en `/docs` y el contrato en `openapi.json`.

- `GET /health`: estado y modos activos.
- `POST /transactions/evaluate`: evalúa una `TransactionInput`.
- `POST /transactions/evaluate/batch`: máximo 200 transacciones.
- `POST /documents/validate`: multipart con `file`, `document_type`, `reference_id` y `expected_fields` JSON opcionales.
- `POST /documents/references`: registra firma o plantilla.
- `GET /documents/{trace_id}/evidence`: regiones forenses.
- `GET /cases` y `GET /cases/{trace_id}`: trazas.
- `POST /feedback`: etiqueta humana e indexación en memoria.
- `GET /metrics`: volumen, revisión, bloqueo, latencia y costo.

Los errores de validación usan HTTP 422 y los identificadores inexistentes HTTP 404. Las respuestas al cliente no exponen reglas, modelos, umbrales ni señales forenses.

