from abc import ABC, abstractmethod
from typing import Any, Generic, TypeVar

from centinela.schemas.common import Decision

InputT = TypeVar("InputT")


class BaseAgent(ABC, Generic[InputT]):
    """Contrato explícito del ciclo perceive → enrich → reason → decide → explain → log."""

    @abstractmethod
    def perceive(self, input_data: InputT) -> dict[str, Any]: ...

    @abstractmethod
    def enrich(self, context: dict[str, Any]) -> dict[str, Any]: ...

    @abstractmethod
    def reason(self, context: dict[str, Any]) -> dict[str, Any]: ...

    @abstractmethod
    def decide(self, context: dict[str, Any], reasoning: dict[str, Any]) -> Decision: ...

    @abstractmethod
    def evaluate(self, input_data: InputT) -> Decision: ...

