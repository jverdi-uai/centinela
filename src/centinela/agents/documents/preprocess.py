import io
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pypdfium2 as pdfium
from PIL import Image, ImageOps


@dataclass
class PreprocessedDocument:
    pages: list[Image.Image]
    image_quality: float
    metadata: dict[str, Any]


def _quality(image: Image.Image) -> float:
    gray = np.asarray(ImageOps.grayscale(image).resize((min(image.width, 800), min(image.height, 1000))), dtype=float)
    contrast = min(1.0, float(gray.std()) / 45.0)
    gx = np.abs(np.diff(gray, axis=1)).mean() if gray.shape[1] > 1 else 0
    gy = np.abs(np.diff(gray, axis=0)).mean() if gray.shape[0] > 1 else 0
    sharpness = min(1.0, float(gx + gy) / 18.0)
    return round(0.45 * contrast + 0.55 * sharpness, 4)


def preprocess_document(filename: str, content: bytes, max_pages: int = 5) -> PreprocessedDocument:
    suffix = Path(filename).suffix.lower()
    if suffix == ".pdf":
        document = pdfium.PdfDocument(content)
        if len(document) > max_pages:
            raise ValueError(f"El PDF supera el máximo de {max_pages} páginas")
        pages = [page.render(scale=150 / 72).to_pil().convert("RGB") for page in document]
        metadata = {"format": "pdf", "pages": len(pages)}
    elif suffix in {".jpg", ".jpeg", ".png"}:
        source = Image.open(io.BytesIO(content))
        metadata = {"format": suffix.removeprefix("."), "exif": {str(k): str(v) for k, v in source.getexif().items()}}
        pages = [ImageOps.exif_transpose(source).convert("RGB")]
    else:
        raise ValueError("Formato no soportado. Use JPG, PNG o PDF")
    if not pages:
        raise ValueError("El documento no contiene páginas")
    return PreprocessedDocument(pages, round(sum(_quality(page) for page in pages) / len(pages), 4), metadata)


def compose_pages(pages: list[Image.Image], max_width: int = 1400) -> bytes:
    resized: list[Image.Image] = []
    for page in pages:
        ratio = min(1.0, max_width / page.width)
        resized.append(page.resize((round(page.width * ratio), round(page.height * ratio))))
    width = max(page.width for page in resized)
    height = sum(page.height for page in resized)
    canvas = Image.new("RGB", (width, height), "white")
    y = 0
    for page in resized:
        canvas.paste(page, (0, y))
        y += page.height
    output = io.BytesIO()
    canvas.save(output, format="JPEG", quality=88, optimize=True)
    return output.getvalue()
