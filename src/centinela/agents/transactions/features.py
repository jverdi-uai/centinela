from typing import Any

from .schemas import TransactionInput


def derive_features(transaction: TransactionInput) -> dict[str, Any]:
    hour = transaction.timestamp.hour
    return {
        "amount_ratio": round(transaction.amount / transaction.origin_account.avg_monthly_amount, 4),
        "velocity_score": min(1.0, transaction.behavior.tx_last_hour / 6),
        "new_device_and_new_beneficiary": (
            transaction.device.is_new_device and transaction.destination_account.is_new_beneficiary
        ),
        "night_hours": hour < 6 or hour >= 23,
        "geo_anomaly": transaction.geo.distance_from_home_km >= 100,
    }


def canonical_description(transaction: TransactionInput, features: dict[str, Any]) -> str:
    """Descripción sin identificadores de cuenta, dispositivo ni transacción."""
    amount_band = "muy_alto" if features["amount_ratio"] >= 3 else "alto" if features["amount_ratio"] >= 1.5 else "normal"
    distance_band = "remota" if transaction.geo.distance_from_home_km >= 100 else "cercana"
    return (
        f"operacion={transaction.type}; canal={transaction.channel}; monto_relativo={amount_band}; "
        f"beneficiario_nuevo={transaction.destination_account.is_new_beneficiary}; "
        f"dispositivo_nuevo={transaction.device.is_new_device}; pais_ip_coincide="
        f"{transaction.device.ip_country == transaction.origin_account.country}; vpn={transaction.device.vpn}; "
        f"ubicacion={distance_band}; velocidad_hora={min(transaction.behavior.tx_last_hour, 9)}; "
        f"fallos_login={min(transaction.behavior.failed_logins_24h, 9)}; horario_nocturno={features['night_hours']}"
    )

