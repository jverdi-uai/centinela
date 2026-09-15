import time
import uuid
from collections import defaultdict, deque
from typing import Any

from centinela.agents.base import BaseAgent
from centinela.config import Settings, get_settings
from centinela.core.llm import LLMClient
from centinela.core.mock import mock_customer_message
from centinela.core.rules import transaction_fuzzy_score
from centinela.core.tracing import save_trace
from centinela.core.vector_store import SQLiteVectorStore
from centinela.db import init_db
from centinela.schemas.common import Decision, Evidence

from .features import canonical_description, derive_features
from .prompts import PROMPT_VERSION, SYSTEM_PROMPT
from .rules_config import evaluate_rules
from .schemas import TransactionInput, TransactionReasoning


class TransactionAgent(BaseAgent[TransactionInput]):
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        init_db()
        self.llm = LLMClient(self.settings)
        self.vector_store = SQLiteVectorStore(self.settings, self.llm)
        self.destination_accounts: dict[str, deque[str]] = defaultdict(lambda: deque(maxlen=20))
        self.device_accounts: dict[str, set[str]] = defaultdict(set)

    def perceive(self, input_data: TransactionInput) -> dict[str, Any]:
        return {"transaction": input_data, "features": derive_features(input_data)}

    def enrich(self, context: dict[str, Any]) -> dict[str, Any]:
        transaction: TransactionInput = context["transaction"]
        features = context["features"]
        rule_evidence, rule_score = evaluate_rules(transaction, features)
        fuzzy_score = transaction_fuzzy_score(
            features["amount_ratio"], transaction.behavior.tx_last_hour, transaction.geo.distance_from_home_km
        )
        rules_fuzzy = min(1.0, 0.65 * rule_score + 0.35 * fuzzy_score)
        canonical = canonical_description(transaction, features)
        neighbors = self.vector_store.search(canonical, "transaction", 5)
        fraud_neighbors = [n for n in neighbors if n.label == "fraude_confirmado"]
        similarity_score = max((n.similarity for n in fraud_neighbors), default=0.0)
        if self.settings.mock_mode and not neighbors:
            similarity_score = min(0.95, 0.05 + 0.75 * rules_fuzzy)
        evidence: list[Evidence] = list(rule_evidence)
        if neighbors:
            evidence.append(Evidence(
                type="similarity", name="casos_revisados_cercanos", value=[n.reference_id for n in neighbors],
                weight=0.25, detail=f"{len(fraud_neighbors)} de {len(neighbors)} vecinos están confirmados como fraude",
            ))

        destination_history = self.destination_accounts[transaction.destination_account.id]
        destination_history.append(transaction.origin_account.id)
        self.device_accounts[transaction.device.id].add(transaction.origin_account.id)
        if len(set(destination_history)) >= 3:
            evidence.append(Evidence(type="consistency", name="destino_compartido", value=len(set(destination_history)), weight=0.30, detail="El destino recibió fondos de tres o más cuentas durante la ventana observada"))
            rules_fuzzy = min(1.0, rules_fuzzy + 0.15)
        if len(self.device_accounts[transaction.device.id]) > 2:
            evidence.append(Evidence(type="consistency", name="dispositivo_compartido", value=len(self.device_accounts[transaction.device.id]), weight=0.30, detail="El dispositivo está asociado a más de dos cuentas"))
            rules_fuzzy = min(1.0, rules_fuzzy + 0.15)

        context.update({
            "evidence": evidence,
            "rule_score": rule_score,
            "fuzzy_score": fuzzy_score,
            "rules_fuzzy_score": round(rules_fuzzy, 4),
            "similarity_score": round(similarity_score, 4),
            "neighbors": [n.__dict__ for n in neighbors],
            "canonical": canonical,
        })
        return context

    def reason(self, context: dict[str, Any]) -> dict[str, Any]:
        if self.settings.mock_mode:
            risk = context["rules_fuzzy_score"]
            score = min(0.98, 0.08 if risk == 0 else 0.30 + risk)
            reasons = [item.detail for item in sorted(context["evidence"], key=lambda e: e.weight, reverse=True)[:4]]
            if not reasons:
                reasons = ["No se detectaron señales de riesgo relevantes"]
            return {
                "score": round(score, 4),
                "confidence": 0.90,
                "reasons": reasons,
                "explanation_customer": "",
                "explanation_analyst": "; ".join(reasons),
                "tokens_in": 0,
                "tokens_out": 0,
                "cost_usd": 0.0,
            }
        payload = {
            "features": context["features"],
            "evidence": [e.model_dump(mode="json") for e in context["evidence"]],
            "scores": {"reglas_fuzzy": context["rules_fuzzy_score"], "similitud": context["similarity_score"]},
        }
        result = self.llm.chat_structured(TransactionReasoning, SYSTEM_PROMPT, payload)
        data = result.output.model_dump()
        data.update(tokens_in=result.tokens_in, tokens_out=result.tokens_out, cost_usd=result.cost_usd)
        return data

    def decide(self, context: dict[str, Any], reasoning: dict[str, Any]) -> Decision:
        score = (
            self.settings.transaction_rules_weight * context["rules_fuzzy_score"]
            + self.settings.transaction_similarity_weight * context["similarity_score"]
            + self.settings.transaction_model_weight * reasoning["score"]
        )
        score = round(min(1.0, max(0.0, score)), 4)
        if score < self.settings.threshold_review:
            actual_verdict = "aprobar"
        elif score < self.settings.threshold_block:
            actual_verdict = "validacion_adicional"
        else:
            actual_verdict = "bloquear"
        returned_verdict = "aprobar" if self.settings.shadow_mode else actual_verdict
        reasons = reasoning["reasons"]
        decision = Decision(
            trace_id=f"tr-{uuid.uuid4().hex}", process="transaction", verdict=returned_verdict,
            score=score, confidence=reasoning["confidence"], reasons=reasons,
            evidence=context["evidence"], requires_human_review=actual_verdict == "bloquear",
            explanation_customer=mock_customer_message("transaction", returned_verdict) if self.settings.mock_mode else reasoning["explanation_customer"],
            explanation_analyst=(f"Veredicto calculado: {actual_verdict}. " + reasoning["explanation_analyst"]),
            model="mock-deterministic" if self.settings.mock_mode else self.settings.openai_chat_model,
            tokens_in=reasoning.get("tokens_in", 0), tokens_out=reasoning.get("tokens_out", 0),
            cost_usd=reasoning.get("cost_usd", 0.0), shadow=self.settings.shadow_mode,
        )
        return decision

    def evaluate(self, input_data: TransactionInput) -> Decision:
        started = time.perf_counter()
        context = self.enrich(self.perceive(input_data))
        reasoning = self.reason(context)
        decision = self.decide(context, reasoning)
        decision.latency_ms = round((time.perf_counter() - started) * 1000, 2)
        log_context = {
            "canonical": context["canonical"],
            "features": context["features"], "rule_score": context["rule_score"],
            "fuzzy_score": context["fuzzy_score"], "rules_fuzzy_score": context["rules_fuzzy_score"],
            "similarity_score": context["similarity_score"], "neighbors": context["neighbors"],
            "weights": {
                "rules_fuzzy": self.settings.transaction_rules_weight,
                "similarity": self.settings.transaction_similarity_weight,
                "model": self.settings.transaction_model_weight,
            },
        }
        save_trace(decision, input_data.model_dump(mode="json"), log_context, PROMPT_VERSION)
        return decision
