import re
from datetime import date, datetime
from typing import Any

from .schemas import Check, ExtractedField


def valid_chilean_rut(value: str) -> bool:
    clean = re.sub(r"[^0-9kK]", "", value)
    if len(clean) < 2:
        return False
    body, verifier = clean[:-1], clean[-1].upper()
    if not body.isdigit():
        return False
    total, multiplier = 0, 2
    for digit in reversed(body):
        total += int(digit) * multiplier
        multiplier = 2 if multiplier == 7 else multiplier + 1
    result = 11 - total % 11
    expected = "0" if result == 11 else "K" if result == 10 else str(result)
    return verifier == expected


def _field(fields: dict[str, ExtractedField], name: str) -> str | None:
    item = fields.get(name)
    return item.value.strip() if item and item.value.strip() else None


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            pass
    return None


def run_checks(fields: dict[str, ExtractedField], expected_fields: dict[str, str] | None, metadata: dict[str, Any]) -> list[Check]:
    checks: list[Check] = []
    rut = _field(fields, "rut")
    if rut:
        ok = valid_chilean_rut(rut)
        checks.append(Check(name="rut_modulo_11", status="pass" if ok else "fail", detail="RUT válido" if ok else "Dígito verificador de RUT inválido", critical=True))
    else:
        checks.append(Check(name="rut_modulo_11", status="pending", detail="El documento no contiene un RUT legible"))

    issued = _parse_date(_field(fields, "fecha_emision"))
    expires = _parse_date(_field(fields, "fecha_vencimiento"))
    if issued and expires:
        ok = issued <= expires and issued <= date.today()
        checks.append(Check(name="consistencia_fechas", status="pass" if ok else "fail", detail="Fechas coherentes" if ok else "La emisión, vencimiento o fecha actual no son coherentes", critical=True))
    elif issued or expires:
        checks.append(Check(name="consistencia_fechas", status="pending", detail="Falta una fecha para completar la comparación"))

    if all(_field(fields, name) for name in ("monto_bruto", "descuentos", "monto_liquido")):
        try:
            parse = lambda x: float(re.sub(r"[^0-9.-]", "", x or "0"))
            balanced = abs(parse(_field(fields, "monto_bruto")) - parse(_field(fields, "descuentos")) - parse(_field(fields, "monto_liquido"))) < 1
            checks.append(Check(name="consistencia_montos", status="pass" if balanced else "fail", detail="Los montos cuadran" if balanced else "Bruto menos descuentos no coincide con el líquido", critical=True))
        except ValueError:
            checks.append(Check(name="consistencia_montos", status="pending", detail="No fue posible interpretar todos los montos"))

    for key, expected in (expected_fields or {}).items():
        actual = _field(fields, key)
        status = "pass" if actual and actual.casefold() == str(expected).strip().casefold() else "fail"
        checks.append(Check(name=f"campo_esperado_{key}", status=status, detail="Coincide con el valor esperado" if status == "pass" else "No coincide con el valor esperado", critical=key in {"rut", "nombre"}))

    metadata_text = str(metadata).casefold()
    edited = any(token in metadata_text for token in ("photoshop", "gimp", "image editor", "editor"))
    checks.append(Check(name="metadatos_edicion", status="warn" if edited else "pass", detail="Los metadatos mencionan software de edición" if edited else "Sin software de edición declarado"))
    return checks

