import io

from PIL import Image, ImageDraw

from centinela.agents.documents import DocumentAgent


def sample_image() -> bytes:
    image = Image.new("RGB", (1000, 700), "white")
    draw = ImageDraw.Draw(image)
    draw.rectangle((30, 30, 970, 670), outline="black", width=5)
    for index in range(12):
        draw.text((80, 80 + index * 40), f"DOCUMENTO SINTETICO LINEA {index} 1234567890", fill="black")
    output = io.BytesIO()
    image.save(output, "PNG")
    return output.getvalue()


def test_document_mock_verdicts_and_critical_check():
    agent = DocumentAgent()
    content = sample_image()
    authentic = agent.evaluate({"filename": "cedula_ok.png", "content": content, "document_type": "cedula", "expected_fields": None, "reference_id": None})
    invalid = agent.evaluate({"filename": "cedula_rut_invalido.png", "content": content, "document_type": "cedula", "expected_fields": None, "reference_id": None})
    altered = agent.evaluate({"filename": "contrato_firma_pegada.png", "content": content, "document_type": "contrato", "expected_fields": None, "reference_id": None})
    metadata = agent.evaluate({"filename": "comprobante_metadatos_editor.png", "content": content, "document_type": "comprobante_domicilio", "expected_fields": None, "reference_id": None})
    assert authentic.verdict == "autentico"
    assert invalid.verdict in {"sospechoso", "falso"}
    assert any(check.name == "rut_modulo_11" and check.status == "fail" for check in invalid.checks)
    assert altered.verdict == "falso"
    assert metadata.verdict == "sospechoso"
