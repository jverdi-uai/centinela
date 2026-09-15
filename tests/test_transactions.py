from copy import deepcopy

from centinela.agents.transactions import TransactionAgent, TransactionInput
from centinela.config import Settings


BASE = {
    "transaction_id": "TX-TEST", "timestamp": "2026-09-08T14:32:10-03:00", "amount": 85000,
    "currency": "CLP", "channel": "app_movil", "type": "pago",
    "origin_account": {"id": "ACC-A", "age_days": 1450, "avg_monthly_amount": 900000, "country": "CL"},
    "destination_account": {"id": "ACC-B", "bank": "Banco", "is_new_beneficiary": False, "country": "CL"},
    "device": {"id": "DEV-A", "is_new_device": False, "os": "Android", "ip_country": "CL", "vpn": False},
    "geo": {"lat": -33.45, "lon": -70.66, "distance_from_home_km": 2.1},
    "behavior": {"tx_last_hour": 0, "tx_last_24h": 2, "failed_logins_24h": 0, "session_seconds": 180},
    "customer_profile": {"segment": "persona_natural", "risk_tier": "medio"},
}


def test_three_demo_scenarios():
    agent = TransactionAgent()
    legitimate = agent.evaluate(TransactionInput.model_validate(BASE))

    doubtful_data = deepcopy(BASE)
    doubtful_data.update(transaction_id="TX-D", amount=1_250_000, type="transferencia")
    doubtful_data["destination_account"]["is_new_beneficiary"] = True
    doubtful_data["behavior"].update(tx_last_hour=1, failed_logins_24h=1, session_seconds=95)
    doubtful = agent.evaluate(TransactionInput.model_validate(doubtful_data))

    fraud_data = deepcopy(BASE)
    fraud_data.update(transaction_id="TX-F", amount=3_900_000, channel="web", type="transferencia")
    fraud_data["destination_account"]["is_new_beneficiary"] = True
    fraud_data["device"].update(is_new_device=True, ip_country="BR", vpn=True)
    fraud_data["geo"]["distance_from_home_km"] = 640
    fraud_data["behavior"].update(tx_last_hour=3, failed_logins_24h=5, session_seconds=22)
    fraud = agent.evaluate(TransactionInput.model_validate(fraud_data))

    assert [legitimate.verdict, doubtful.verdict, fraud.verdict] == ["aprobar", "validacion_adicional", "bloquear"]
    assert fraud.requires_human_review is True
    assert all(word not in fraud.explanation_customer.casefold() for word in ("regla", "modelo", "umbral", "similitud"))


def test_shadow_mode_returns_approve_but_keeps_review():
    data = deepcopy(BASE)
    data.update(amount=5_000_000)
    data["destination_account"]["is_new_beneficiary"] = True
    data["device"].update(is_new_device=True, ip_country="BR", vpn=True)
    settings = Settings(mock_mode=True, shadow_mode=True, database_url="sqlite:///data/centinela-test.db")
    decision = TransactionAgent(settings).evaluate(TransactionInput.model_validate(data))
    assert decision.verdict == "aprobar"
    assert decision.shadow is True
    assert decision.requires_human_review is True

