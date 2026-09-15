# Arquitectura

```mermaid
flowchart LR
  UI[Canales / web app] --> API[FastAPI]
  API --> TX[TransactionAgent]
  API --> DOC[DocumentAgent]
  TX --> R[Reglas + fuzzy]
  TX --> V[Vector store]
  DOC --> P[Preproceso + checks]
  DOC --> V
  TX --> O[OpenAI estructurado]
  DOC --> O
  TX --> DB[(SQLite trazas)]
  DOC --> DB
  API --> HUMAN[Analista / feedback]
  HUMAN --> V
```

Ambos agentes aplican `perceive → enrich → reason → decide → log`. `MOCK_MODE=true` sustituye únicamente las llamadas externas; conserva reglas, checks, umbrales, trazabilidad y endpoints. Los identificadores se mantienen opacos en la descripción enviada al modelo.

