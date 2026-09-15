from dataclasses import dataclass
from typing import Callable

from centinela.schemas.common import Evidence

from .schemas import TransactionInput


@dataclass(frozen=True)
class Rule:
    name: str
    weight: float
    detail: str
    predicate: Callable[[TransactionInput, dict], bool]


RULES = [
    Rule("beneficiario_y_dispositivo_nuevos", 0.35, "Beneficiario y dispositivo nuevos en la misma sesión", lambda t, f: f["new_device_and_new_beneficiary"]),
    Rule("beneficiario_nuevo", 0.35, "Transferencia a un beneficiario no usado antes", lambda t, f: t.destination_account.is_new_beneficiary),
    Rule("monto_sobre_promedio", 0.30, "Monto superior a tres veces el promedio mensual", lambda t, f: f["amount_ratio"] > 3),
    Rule("alta_velocidad", 0.50, "Más de cinco transacciones durante la última hora", lambda t, f: t.behavior.tx_last_hour > 5),
    Rule("intentos_fallidos", 0.25, "Tres o más inicios de sesión fallidos en 24 horas", lambda t, f: t.behavior.failed_logins_24h >= 3),
    Rule("pais_ip_distinto", 0.30, "El país de la IP difiere del país de la cuenta", lambda t, f: t.device.ip_country != t.origin_account.country),
    Rule("vpn_monto_alto", 0.25, "VPN activa en una operación de monto relativo alto", lambda t, f: t.device.vpn and f["amount_ratio"] >= 1.5),
    Rule("sesion_corta", 0.15, "Operación creada en una sesión menor a 20 segundos", lambda t, f: t.behavior.session_seconds < 20),
    Rule("cuenta_reciente", 0.20, "Cuenta de origen con menos de 30 días", lambda t, f: t.origin_account.age_days < 30),
    Rule("beneficiario_nuevo_monto_alto", 0.25, "Beneficiario nuevo con monto de al menos dos veces el promedio mensual", lambda t, f: t.destination_account.is_new_beneficiary and f["amount_ratio"] >= 2),
    Rule("noche_ubicacion_inusual", 0.30, "Operación nocturna a más de 100 km del domicilio", lambda t, f: f["night_hours"] and f["geo_anomaly"]),
]


def evaluate_rules(transaction: TransactionInput, features: dict) -> tuple[list[Evidence], float]:
    evidence = [
        Evidence(type="rule", name=rule.name, value=True, weight=rule.weight, detail=rule.detail)
        for rule in RULES if rule.predicate(transaction, features)
    ]
    return evidence, min(1.0, round(sum(item.weight for item in evidence), 4))
