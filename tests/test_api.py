import io

from fastapi.testclient import TestClient
from PIL import Image, ImageDraw

from centinela.main import app


def png_bytes() -> bytes:
    image = Image.new("RGB", (1000, 700), "white")
    draw = ImageDraw.Draw(image)
    for y in range(40, 650, 25):
        draw.line((30, y, 970, y), fill="black", width=2)
    output = io.BytesIO()
    image.save(output, "PNG")
    return output.getvalue()


def test_document_endpoint_and_case_trace():
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/documents/validate",
            files={"file": ("cedula_ok.png", png_bytes(), "image/png")},
            data={"document_type": "cedula"},
        )
        assert response.status_code == 200, response.text
        decision = response.json()
        assert decision["process"] == "document"
        detail = client.get(f"/api/v1/cases/{decision['trace_id']}")
        assert detail.status_code == 200
        assert client.get(f"/api/v1/documents/{decision['trace_id']}/evidence").status_code == 200


def test_rejects_unsupported_document():
    with TestClient(app) as client:
        response = client.post("/api/v1/documents/validate", files={"file": ("bad.txt", b"x", "text/plain")})
        assert response.status_code == 422

