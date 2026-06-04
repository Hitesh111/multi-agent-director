from abc import ABC, abstractmethod
from typing import AsyncIterator

from .schemas import LLMConfig, LLMResponse, EmbeddingResponse, Message


class BaseLLMProvider(ABC):
    """Abstract base for all LLM providers.

    Every provider must implement generate, stream, and embeddings.
    Providers are stateless — all config comes from parameters.
    """

    def __init__(self, config: dict):
        self.api_key: str = config.get("api_key", "")
        self.api_base: str = config.get("api_base", "")
        self.default_model: str = config.get("default_model", "")

    @abstractmethod
    async def generate(
        self,
        messages: list[Message],
        config: LLMConfig,
    ) -> LLMResponse:
        ...

    @abstractmethod
    async def stream(
        self,
        messages: list[Message],
        config: LLMConfig,
    ) -> AsyncIterator[str]:
        ...

    @abstractmethod
    async def embeddings(
        self,
        texts: list[str],
        model: str = "",
    ) -> EmbeddingResponse:
        ...

    def _require_api_key(self):
        if not self.api_key or self.api_key.startswith("sk-placeholder"):
            raise ValueError(
                f"{type(self).__name__}: API key not configured. "
                f"Set a valid API key in .env or agent config."
            )

    def _build_headers(self) -> dict:
        self._require_api_key()
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
