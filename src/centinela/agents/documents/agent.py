import io
import time
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from PIL import Image

from centinela.agents.base import BaseAgent
from centinela.config import Settings, get_settings
from centinela.core.llm import LLMClient
from centinela.core.mock import mock_customer_message
from centinela.core.tracing import save_trace
from centinela.core.vector_store import SQLiteVectorStore
from centinela.db import init_db
from centinela.schemas.common import Evidence

from .checks import run_checks
from .preprocess import compose_pages, preprocess_document
from .prompts import EXTRACTION_PROMPT, FORENSICS_PROMPT, PROMPT_VERSION, REASONING_PROMPT
from .schemas import (
    Check, DocumentDecision, DocumentReasoning, DocumentType, ExtractedField,
    Finding, VisionExtraction, VisionForensics,
)


class DocumentAgent(BaseAgent[dict[str, Any]]):
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        init_db()
        self.llm = LLMClient(self.settings)
        self.vector_store = SQLiteVectorStore(self.settings, self.llm)

    def perceive(self, input_data: dict[str, Any]) -> dict[str, Any]:
        content: bytes = input_data["content"]
        if len(content) > self.settings.max_document_mb * 1024 * 1024:
            raise ValueError(f"El archivo supera {self.settings.max_document_mb} MB")
        processed = preprocess_document(input_data["filename"], content, self.settings.max_pdf_pages)
        return {**input_data, "processed": processed, "trace_id": f"doc-{uuid.uuid4().hex}"}

    @staticmethod
    def _mock_extraction(filename: str, document_type: DocumentType | None) -> VisionExtraction:
        name = filename.casefold()
        detected: DocumentType = document_type or next((kind for kind in ("cedula", "comprobante_domicilio", "contrato", "liquidacion", "poder", "firma") if kind in name), "otro")
        fields: dict[str, ExtractedField] = {
            "nombre": ExtractedField(value="Persona Ficticia", confidence=0.98),
            "rut": ExtractedField(value="12.345.678-5", confidence=0.98),
            "fecha_emision": ExtractedField(value="2024-01-10", confidence=0.96),
            "fecha_vencimiento": ExtractedField(value="2030-01-10", confidence=0.96),
        }
        if "rut_invalido" in name:
            fields["rut"] = ExtractedField(value="12.345.678-9", confidence=0.99)
        if "alterada_fecha" in name:
            fields["fecha_vencimiento"] = ExtractedField(value="2023-01-10", confidence=0.99)
        if detected == "liquidacion":
            fields.update({
                "monto_bruto": ExtractedField(value="1000000", confidence=0.97),
                "descuentos": ExtractedField(value="200000", confidence=0.97),
                "monto_liquido": ExtractedField(value="900000" if "editados" in name else "800000", confidence=0.97),
            })
        return VisionExtraction(document_type=detected, fields=fields, layout="Documento sintético centrado con encabezado, cuerpo y firma")

    @staticmethod
    def _mock_forensics(filename: str) -> VisionForensics:
        name = filename.casefold()
        mapping = {
            "alterada_fecha": (0.92, "Tipografía distinta en fecha", {"x": 0.55, "y": 0.35, "w": 0.25, "h": 0.08}),
            "firma_pegada": (0.90, "Borde de recorte alrededor de la firma", {"x": 0.55, "y": 0.72, "w": 0.28, "h": 0.12}),
            "montos_editados": (0.88, "Monto con línea base y tipografía distintas", {"x": 0.58, "y": 0.52, "w": 0.22, "h": 0.08}),
            "texto_tipografia": (0.91, "Bloque de texto con tipografía y fondo distintos", {"x": 0.18, "y": 0.48, "w": 0.64, "h": 0.16}),
            "metadatos_editor": (0.20, "Sin alteración visual concluyente", None),
            "rut_invalido": (0.18, "Sin alteración visual concluyente", None),
        }
        match = next((value for token, value in mapping.items() if token in name), None)
        if not match:
            return VisionForensics(manipulation_score=0.05, findings=[])
        score, detail, region = match
        return VisionForensics(manipulation_score=score, findings=[Finding(name="hallazgo_forense", confidence=score, detail=detail, region=region)])

    def enrich(self, context: dict[str, Any]) -> dict[str, Any]:
        filename = context["filename"]
        requested_type = context.get("document_type")
        composite = compose_pages(context["processed"].pages)
        if self.settings.mock_mode:
            extraction = self._mock_extraction(filename, requested_type)
            forensics = self._mock_forensics(filename)
            tokens_in = tokens_out = 0
            vision_cost = 0.0
        else:
            extracted = self.llm.describe_image(VisionExtraction, composite, "image/jpeg", EXTRACTION_PROMPT)
            forensic = self.llm.describe_image(VisionForensics, composite, "image/jpeg", FORENSICS_PROMPT)
            extraction = extracted.output
            forensics = forensic.output
            tokens_in = extracted.tokens_in + forensic.tokens_in
            tokens_out = extracted.tokens_out + forensic.tokens_out
            vision_cost = extracted.cost_usd + forensic.cost_usd

        metadata = dict(context["processed"].metadata)
        if "metadatos_editor" in filename.casefold():
            metadata["software"] = "Synthetic Image Editor"
        checks = run_checks(extraction.fields, context.get("expected_fields"), metadata)
        fail_weight = sum(1.0 if check.critical else 0.6 for check in checks if check.status == "fail")
        warn_weight = sum(0.60 for check in checks if check.status == "warn")
        checks_score = min(1.0, max(fail_weight, warn_weight))
        canonical = f"tipo={extraction.document_type}; campos={','.join(sorted(extraction.fields))}; layout={extraction.layout}"
        neighbors = self.vector_store.search(canonical, "document", 5)
        evidence: list[Evidence] = [
            Evidence(type="vision", name=finding.name, value=finding.confidence, weight=finding.confidence, detail=finding.detail, region=finding.region)
            for finding in forensics.findings
        ]
        evidence.extend(
            Evidence(type="consistency" if check.name != "metadatos_edicion" else "metadata", name=check.name, value=check.status, weight=1.0 if check.critical else 0.45, detail=check.detail)
            for check in checks if check.status in {"fail", "warn", "pending"}
        )
        if neighbors:
            evidence.append(Evidence(type="similarity", name="plantillas_y_casos_cercanos", value=[n.reference_id for n in neighbors], weight=0.25, detail="Comparación con memoria de documentos revisados"))
        context.update({
            "composite": composite, "extraction": extraction, "forensics": forensics,
            "checks": checks, "checks_score": checks_score, "canonical": canonical,
            "neighbors": [n.__dict__ for n in neighbors], "evidence": evidence,
            "tokens_in": tokens_in, "tokens_out": tokens_out, "vision_cost": vision_cost,
        })
        return context

    def reason(self, context: dict[str, Any]) -> dict[str, Any]:
        if self.settings.mock_mode:
            base = max(context["forensics"].manipulation_score, context["checks_score"] * 0.75)
            reasons = [e.detail for e in sorted(context["evidence"], key=lambda e: e.weight, reverse=True)[:5]] or ["No se detectaron inconsistencias relevantes"]
            return {"score": round(base, 4), "confidence": 0.90, "reasons": reasons, "explanation_customer": "", "explanation_analyst": "; ".join(reasons), "tokens_in": context["tokens_in"], "tokens_out": context["tokens_out"], "cost_usd": context["vision_cost"]}
        payload = {
            "document_type": context["extraction"].document_type,
            "image_quality": context["processed"].image_quality,
            "checks": [c.model_dump() for c in context["checks"]],
            "findings": [f.model_dump() for f in context["forensics"].findings],
        }
        result = self.llm.chat_structured(DocumentReasoning, REASONING_PROMPT, payload)
        data = result.output.model_dump()
        data.update(tokens_in=context["tokens_in"] + result.tokens_in, tokens_out=context["tokens_out"] + result.tokens_out, cost_usd=context["vision_cost"] + result.cost_usd)
        return data

    def decide(self, context: dict[str, Any], reasoning: dict[str, Any]) -> DocumentDecision:
        score = (
            self.settings.document_vision_weight * context["forensics"].manipulation_score
            + self.settings.document_checks_weight * context["checks_score"]
            + self.settings.document_model_weight * reasoning["score"]
        )
        score = round(min(1.0, max(0.0, score)), 4)
        critical_fail = any(check.critical and check.status == "fail" for check in context["checks"])
        if context["processed"].image_quality < 0.4:
            actual_verdict = "sospechoso"
            reasoning["reasons"] = ["Calidad insuficiente, solicitar nueva captura", *reasoning["reasons"]]
        elif score >= self.settings.threshold_block or context["forensics"].manipulation_score >= 0.85:
            actual_verdict = "falso"
        elif score >= self.settings.threshold_review or critical_fail:
            actual_verdict = "sospechoso"
        else:
            actual_verdict = "autentico"
        returned_verdict = "autentico" if self.settings.shadow_mode else actual_verdict
        return DocumentDecision(
            trace_id=context["trace_id"], process="document", verdict=returned_verdict, score=score,
            confidence=reasoning["confidence"], reasons=reasoning["reasons"], evidence=context["evidence"],
            requires_human_review=actual_verdict in {"sospechoso", "falso"},
            explanation_customer=mock_customer_message("document", returned_verdict) if self.settings.mock_mode else reasoning["explanation_customer"],
            explanation_analyst=f"Veredicto calculado: {actual_verdict}. {reasoning['explanation_analyst']}",
            model="mock-deterministic" if self.settings.mock_mode else self.settings.openai_vision_model,
            tokens_in=reasoning.get("tokens_in", 0), tokens_out=reasoning.get("tokens_out", 0), cost_usd=reasoning.get("cost_usd", 0), shadow=self.settings.shadow_mode,
            document_type_detected=context["extraction"].document_type, fields=context["extraction"].fields,
            checks=context["checks"], pages_analyzed=len(context["processed"].pages), image_quality=context["processed"].image_quality,
        )

    def _store_pages(self, context: dict[str, Any]) -> None:
        target = Path("data/traces") / context["trace_id"]
        target.mkdir(parents=True, exist_ok=True)
        for index, page in enumerate(context["processed"].pages, 1):
            page.save(target / f"page-{index}.jpg", format="JPEG", quality=88)

    def cleanup_expired_traces(self, now: datetime | None = None) -> int:
        cutoff = (now or datetime.now(timezone.utc)) - timedelta(days=self.settings.trace_retention_days)
        removed = 0
        root = Path("data/traces")
        if not root.exists():
            return 0
        for directory in root.iterdir():
            if directory.is_dir() and datetime.fromtimestamp(directory.stat().st_mtime, timezone.utc) < cutoff:
                for file in directory.iterdir():
                    file.unlink()
                directory.rmdir()
                removed += 1
        return removed

    def evaluate(self, input_data: dict[str, Any]) -> DocumentDecision:
        started = time.perf_counter()
        context = self.enrich(self.perceive(input_data))
        reasoning = self.reason(context)
        decision = self.decide(context, reasoning)
        decision.latency_ms = round((time.perf_counter() - started) * 1000, 2)
        self._store_pages(context)
        self.cleanup_expired_traces()
        safe_input = {"filename": context["filename"], "document_type": context.get("document_type"), "expected_fields": context.get("expected_fields"), "size_bytes": len(context["content"])}
        log_context = {
            "canonical": context["canonical"],
            "metadata": context["processed"].metadata, "forensics_score": context["forensics"].manipulation_score,
            "checks_score": context["checks_score"], "neighbors": context["neighbors"],
            "weights": {"vision": self.settings.document_vision_weight, "checks": self.settings.document_checks_weight, "model": self.settings.document_model_weight},
        }
        save_trace(decision, safe_input, log_context, PROMPT_VERSION)
        return decision
