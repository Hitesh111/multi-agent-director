from typing import AsyncIterator

import httpx

from ..base import BaseLLMProvider
from ..schemas import LLMConfig, LLMResponse, EmbeddingResponse, Message, TokenUsage


class OpenCodeProvider(BaseLLMProvider):
    """OpenCode API provider.

    Uses the OpenAI-compatible endpoint. Same interface as DeepSeek
    but configured for the OpenCode API base URL and model names.
    """

    def _build_payload(self, messages: list[Message], config: LLMConfig) -> dict:
        return {
            "model": config.model or self.default_model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": config.temperature,
            "max_tokens": config.max_tokens,
            "top_p": config.top_p,
            "stop": config.stop_sequences,
        }

    async def generate(
        self,
        messages: list[Message],
        config: LLMConfig,
    ) -> LLMResponse:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                f"{self.api_base}/chat/completions",
                headers=self._build_headers(),
                json=self._build_payload(messages, config),
            )
            resp.raise_for_status()
            data = resp.json()

            choice = data["choices"][0]
            usage_data = data.get("usage", {})
            usage = TokenUsage(
                prompt_tokens=usage_data.get("prompt_tokens", 0),
                completion_tokens=usage_data.get("completion_tokens", 0),
                total_tokens=usage_data.get("total_tokens", 0),
            )

            return LLMResponse(
                content=choice["message"]["content"],
                usage=usage,
                model=data.get("model", ""),
                finish_reason=choice.get("finish_reason", ""),
                raw=data,
            )

    async def stream(
        self,
        messages: list[Message],
        config: LLMConfig,
    ) -> AsyncIterator[str]:
        payload = self._build_payload(messages, config)
        payload["stream"] = True

        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream(
                "POST",
                f"{self.api_base}/chat/completions",
                headers=self._build_headers(),
                json=payload,
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data_str = line[6:]
                        if data_str.strip() == "[DONE]":
                            break
                        import json

                        chunk = json.loads(data_str)
                        delta = chunk.get("choices", [{}])[0].get("delta", {})
                        content = delta.get("content", "")
                        if content:
                            yield content

    async def embeddings(
        self,
        texts: list[str],
        model: str = "",
    ) -> EmbeddingResponse:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                f"{self.api_base}/embeddings",
                headers=self._build_headers(),
                json={
                    "model": model or self.default_model,
                    "input": texts,
                },
            )
            resp.raise_for_status()
            data = resp.json()

            embeddings_list = [item["embedding"] for item in data["data"]]
            usage_data = data.get("usage", {})
            usage = TokenUsage(
                prompt_tokens=usage_data.get("prompt_tokens", 0),
                total_tokens=usage_data.get("total_tokens", 0),
            )

            return EmbeddingResponse(
                embeddings=embeddings_list,
                model=data.get("model", ""),
                usage=usage,
            )
