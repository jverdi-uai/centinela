import base64
from dataclasses import dataclass
from typing import Any, TypeVar

from openai import OpenAI
from pydantic import BaseModel

from centinela.config import Settings, get_settings

T = TypeVar("T", bound=BaseModel)


@dataclass
class LLMResult:
    output: BaseModel
    tokens_in: int
    tokens_out: int
    cost_usd: float


class LLMClient:
    """Adaptador único para chat estructurado, visión y embeddings.

    Los agentes nunca construyen un cliente OpenAI directamente. Esto mantiene los
    secretos y el cálculo de costo en una sola frontera auditable.
    """

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self._client: OpenAI | None = None

    @property
    def client(self) -> OpenAI:
        if self.settings.mock_mode:
            raise RuntimeError("El cliente OpenAI no está disponible en MOCK_MODE")
        if not self.settings.openai_api_key:
            raise RuntimeError("Falta OPENAI_API_KEY. Configure .env o active MOCK_MODE=true")
        if self._client is None:
            self._client = OpenAI(api_key=self.settings.openai_api_key, timeout=30, max_retries=2)
        return self._client

    def _cost(self, tokens_in: int, tokens_out: int) -> float:
        return round(
            tokens_in / 1_000_000 * self.settings.model_input_usd_per_million
            + tokens_out / 1_000_000 * self.settings.model_output_usd_per_million,
            8,
        )

    def chat_structured(self, schema: type[T], system: str, payload: dict[str, Any], model: str | None = None) -> LLMResult:
        response = self.client.responses.parse(
            model=model or self.settings.openai_chat_model,
            store=False,
            temperature=0,
            input=[
                {"role": "system", "content": system},
                {"role": "user", "content": str(payload)},
            ],
            text_format=schema,
        )
        parsed = response.output_parsed
        if parsed is None:
            raise RuntimeError("El modelo no devolvió una salida estructurada")
        usage = response.usage
        tokens_in = int(getattr(usage, "input_tokens", 0) or 0)
        tokens_out = int(getattr(usage, "output_tokens", 0) or 0)
        return LLMResult(parsed, tokens_in, tokens_out, self._cost(tokens_in, tokens_out))

    def describe_image(self, schema: type[T], image_bytes: bytes, media_type: str, prompt: str) -> LLMResult:
        encoded = base64.b64encode(image_bytes).decode("ascii")
        response = self.client.responses.parse(
            model=self.settings.openai_vision_model,
            store=False,
            temperature=0,
            input=[{
                "role": "user",
                "content": [
                    {"type": "input_text", "text": prompt},
                    {"type": "input_image", "image_url": f"data:{media_type};base64,{encoded}"},
                ],
            }],
            text_format=schema,
        )
        parsed = response.output_parsed
        if parsed is None:
            raise RuntimeError("La visión no devolvió una salida estructurada")
        usage = response.usage
        tokens_in = int(getattr(usage, "input_tokens", 0) or 0)
        tokens_out = int(getattr(usage, "output_tokens", 0) or 0)
        return LLMResult(parsed, tokens_in, tokens_out, self._cost(tokens_in, tokens_out))

    def embed(self, texts: list[str]) -> tuple[list[list[float]], int, float]:
        response = self.client.embeddings.create(model=self.settings.openai_embedding_model, input=texts)
        vectors = [item.embedding for item in response.data]
        tokens = int(getattr(response.usage, "total_tokens", 0) or 0)
        cost = round(tokens / 1_000_000 * self.settings.embedding_usd_per_million, 8)
        return vectors, tokens, cost
