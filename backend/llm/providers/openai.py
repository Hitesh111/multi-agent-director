import json
from typing import AsyncIterator

import httpx

from ..base import BaseLLMProvider
from ..schemas import LLMConfig, LLMResponse, EmbeddingResponse, Message, TokenUsage


class OpenAIProvider(BaseLLMProvider):
    """OpenAI API provider.

    Uses the OpenAI API at api.openai.com/v1.
    Supports GPT-4, GPT-4o, GPT-4o-mini, o1, o3, and all OpenAI models.
    """

    def _build_headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def _build_payload(self, messages: list[Message], config: LLMConfig) -> dict:
        formatted = []
        for m in messages:
            content = m.content
            if isinstance(content, str) and content.startswith('{"type": "multimodal"'):
                try:
                    parsed = json.loads(content)
                    if parsed.get("type") == "multimodal":
                        content = [
                            {"type": "text", "text": parsed.get("text", "")},
                            {"type": "image_url", "image_url": {"url": parsed.get("image_url", "")}},
                        ]
                except Exception:
                    pass
            formatted.append({"role": m.role, "content": content})

        return {
            "model": config.model or self.default_model,
            "messages": formatted,
            "temperature": config.temperature,
            "max_tokens": config.max_tokens,
            "top_p": config.top_p,
            "stop": config.stop_sequences,
        }

    async def generate(self, messages: list[Message], config: LLMConfig) -> LLMResponse:
        payload = self._build_payload(messages, config)

        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                f"{self.api_base}/chat/completions",
                headers=self._build_headers(),
                json=payload,
            )
            if resp.status_code == 402:
                error_data = resp.json()
                raise ValueError(f"LLM API Error (status 402): {error_data}")
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

    async def stream(self, messages: list[Message], config: LLMConfig) -> AsyncIterator[str]:
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
                        chunk = json.loads(data_str)
                        delta = chunk.get("choices", [{}])[0].get("delta", {})
                        content = delta.get("content", "")
                        if content:
                            yield content

    async def embeddings(self, texts: list[str], model: str = "") -> EmbeddingResponse:
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
