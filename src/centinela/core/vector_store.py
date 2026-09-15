import hashlib
import math
import re
from dataclasses import dataclass
from typing import Any, Protocol

import numpy as np
from sqlalchemy import select
from sqlalchemy.orm import Session

from centinela.config import Settings, get_settings
from centinela.core.llm import LLMClient
from centinela.db import VectorRecord, engine


@dataclass
class Neighbor:
    reference_id: str
    label: str
    similarity: float
    metadata: dict[str, Any]


class VectorStore(Protocol):
    def add(self, reference_id: str, kind: str, label: str, text: str, metadata: dict[str, Any] | None = None) -> None: ...
    def search(self, text: str, kind: str, limit: int = 5) -> list[Neighbor]: ...


def deterministic_embedding(text: str, dimensions: int = 64) -> list[float]:
    values = [0.0] * dimensions
    tokens = re.findall(r"[a-záéíóúñ0-9_]+", text.casefold())
    for token in tokens:
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        index = int.from_bytes(digest[:4], "big") % dimensions
        sign = 1.0 if digest[4] % 2 == 0 else -1.0
        values[index] += sign
    norm = math.sqrt(sum(v * v for v in values)) or 1.0
    return [v / norm for v in values]


class SQLiteVectorStore:
    def __init__(self, settings: Settings | None = None, llm: LLMClient | None = None) -> None:
        self.settings = settings or get_settings()
        self.llm = llm or LLMClient(self.settings)

    def _embed(self, text: str) -> list[float]:
        if self.settings.mock_mode:
            return deterministic_embedding(text)
        vectors, _, _ = self.llm.embed([text])
        return vectors[0]

    def add(self, reference_id: str, kind: str, label: str, text: str, metadata: dict[str, Any] | None = None) -> None:
        embedding = self._embed(text)
        with Session(engine) as session:
            existing = session.scalar(select(VectorRecord).where(
                VectorRecord.reference_id == reference_id,
                VectorRecord.kind == kind,
            ))
            if existing:
                existing.label = label
                existing.text = text
                existing.embedding = embedding
                existing.metadata_json = metadata or {}
            else:
                session.add(VectorRecord(
                    reference_id=reference_id, kind=kind, label=label, text=text,
                    embedding=embedding, metadata_json=metadata or {},
                ))
            session.commit()

    def search(self, text: str, kind: str, limit: int = 5) -> list[Neighbor]:
        query = np.asarray(self._embed(text), dtype=float)
        with Session(engine) as session:
            rows = list(session.scalars(select(VectorRecord).where(VectorRecord.kind == kind)))
        neighbors: list[Neighbor] = []
        for row in rows:
            candidate = np.asarray(row.embedding, dtype=float)
            denominator = float(np.linalg.norm(query) * np.linalg.norm(candidate))
            similarity = float(np.dot(query, candidate) / denominator) if denominator else 0.0
            neighbors.append(Neighbor(row.reference_id, row.label, round(similarity, 4), row.metadata_json or {}))
        return sorted(neighbors, key=lambda item: item.similarity, reverse=True)[:limit]
