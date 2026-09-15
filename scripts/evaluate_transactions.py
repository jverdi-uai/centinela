from pathlib import Path
from statistics import median

from centinela.agents.transactions import TransactionAgent
from load_xlsx import load_transactions


def safe_div(numerator: int, denominator: int) -> float:
    return numerator / denominator if denominator else 0.0


def main() -> None:
    agent = TransactionAgent()
    rows = load_transactions("data/synthetic/datos_prueba_centinela.xlsx")
    results = [(label, agent.evaluate(transaction)) for transaction, label, _ in rows]
    tp = sum(label == "fraude" and decision.verdict == "bloquear" for label, decision in results)
    fn = sum(label == "fraude" and decision.verdict != "bloquear" for label, decision in results)
    fp = sum(label == "legitimo" and decision.verdict == "bloquear" for label, decision in results)
    tn = sum(label == "legitimo" and decision.verdict != "bloquear" for label, decision in results)
    latencies = sorted(decision.latency_ms for _, decision in results)
    p95 = latencies[round((len(latencies) - 1) * 0.95)]
    total_cost = sum(decision.cost_usd for _, decision in results)
    report = f"""# Evaluación de transacciones

Modo: `{agent.settings.mock_mode and 'mock' or 'OpenAI'}` · Casos: {len(results)}

| Métrica | Resultado |
|---|---:|
| Precisión | {safe_div(tp, tp + fp):.3f} |
| Recall | {safe_div(tp, tp + fn):.3f} |
| Tasa de falsos positivos | {safe_div(fp, fp + tn):.3f} |
| Latencia p50 | {median(latencies):.2f} ms |
| Latencia p95 | {p95:.2f} ms |
| Costo total | USD {total_cost:.6f} |
| Costo por evento | USD {safe_div(total_cost, len(results)):.8f} |

Los positivos predichos son decisiones `bloquear`; `validacion_adicional` se mantiene como control intermedio.
"""
    Path("reports").mkdir(exist_ok=True)
    Path("reports/transactions_eval.md").write_text(report, encoding="utf-8")
    print(report)


if __name__ == "__main__":
    main()
