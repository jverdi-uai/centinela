from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, PngImagePlugin


CASES = [
    ("cedula_ok.png", "CÉDULA SINTÉTICA\nPersona Ficticia\nRUT 12.345.678-5\nEmisión 2024-01-10\nVencimiento 2030-01-10"),
    ("comprobante_domicilio_ok.png", "LUZ DEL VALLE S.A. — FICTICIO\nPersona Ficticia\nDirección de prueba 123\nTotal $25.000"),
    ("contrato_ok.png", "CONTRATO SINTÉTICO\nAcuerdo académico sin validez legal\nPersona Ficticia\nFirma ficticia"),
    ("liquidacion_ok.png", "LIQUIDACIÓN SINTÉTICA\nBruto $1.000.000\nDescuentos $200.000\nLíquido $800.000"),
    ("poder_ok.png", "PODER SINTÉTICO\nPersona Ficticia\nRUT 12.345.678-5\nFirma ficticia"),
    ("firma_referencia.png", "FIRMA SINTÉTICA DE REFERENCIA\nPersona Ficticia"),
    ("cedula_alterada_fecha.png", "CÉDULA SINTÉTICA ALTERADA\nEmisión 2024-01-10\nVencimiento 2023-01-10\n[FECHA RETOCADA]"),
    ("cedula_rut_invalido.png", "CÉDULA SINTÉTICA ALTERADA\nRUT 12.345.678-9\n[DÍGITO CAMBIADO]"),
    ("contrato_firma_pegada.png", "CONTRATO SINTÉTICO ALTERADO\nFirma copiada\n[BORDE DE RECORTE]"),
    ("liquidacion_montos_editados.png", "LIQUIDACIÓN SINTÉTICA ALTERADA\nBruto $1.000.000\nDescuentos $200.000\nLíquido $900.000"),
    ("comprobante_metadatos_editor.png", "COMPROBANTE SINTÉTICO\nContenido visual coherente\n[METADATOS DE EDITOR]"),
    ("poder_texto_tipografia.png", "PODER SINTÉTICO ALTERADO\nCláusula añadida con otra tipografía\n[FONDO DISTINTO]"),
]


def main() -> None:
    target = Path("data/samples")
    target.mkdir(parents=True, exist_ok=True)
    font = ImageFont.truetype("arial.ttf", 32)
    title = ImageFont.truetype("arialbd.ttf", 42)
    for filename, text in CASES:
        image = Image.new("RGB", (1200, 800), "#f9fafb")
        draw = ImageDraw.Draw(image)
        draw.rectangle((45, 45, 1155, 755), outline="#0b7285", width=5)
        draw.text((90, 90), "CENTINELA · DOCUMENTO DE PRUEBA", fill="#0b7285", font=title)
        draw.multiline_text((90, 190), text, fill="#151a21", font=font, spacing=22)
        draw.line((90, 650, 500, 650), fill="#151a21", width=3)
        metadata = PngImagePlugin.PngInfo()
        metadata.add_text("Synthetic", "true")
        if "metadatos_editor" in filename:
            metadata.add_text("Software", "Synthetic Image Editor")
        image.save(target / filename, pnginfo=metadata)
    print(f"Generados {len(CASES)} documentos sintéticos en {target}")


if __name__ == "__main__":
    main()

