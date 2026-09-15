def ramp(value: float, low: float, high: float) -> float:
    if value <= low:
        return 0.0
    if value >= high:
        return 1.0
    return (value - low) / (high - low)


def transaction_fuzzy_score(amount_ratio: float, tx_last_hour: int, distance_km: float) -> float:
    amount = ramp(amount_ratio, 0.8, 3.0)
    velocity = ramp(float(tx_last_hour), 1.0, 6.0)
    distance = ramp(distance_km, 20.0, 500.0)
    return round(0.45 * amount + 0.35 * velocity + 0.20 * distance, 4)

