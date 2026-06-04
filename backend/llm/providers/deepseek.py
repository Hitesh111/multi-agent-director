import asyncio
import time
from typing import AsyncIterator, ClassVar

import httpx

from ..base import BaseLLMProvider
from ..schemas import LLMConfig, LLMResponse, EmbeddingResponse, Message, TokenUsage

_rate_limiters: dict[str, asyncio.Lock] = {}


class DeepSeekProvider(BaseLLMProvider):
    """DeepSeek API provider.

    Uses the OpenAI-compatible endpoint at api.deepseek.com/v1.
    Supports chat completions, streaming, and embeddings.
    """

    _base_locks: ClassVar[dict[tuple, asyncio.Lock]] = {}
    _last_request: ClassVar[dict[tuple, float]] = {}
    _max_retries: int = 8

    def __init__(self, config: dict):
        super().__init__(config)
        self._max_retries = config.get("max_retries", 8)

    def _build_payload(self, messages: list[Message], config: LLMConfig) -> dict:
        formatted_messages = []
        for m in messages:
            content = m.content
            if isinstance(content, str) and content.startswith('{"type": "multimodal"'):
                try:
                    import json
                    parsed = json.loads(content)
                    if parsed.get("type") == "multimodal":
                        content = [
                            {"type": "text", "text": parsed.get("text", "")},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": parsed.get("image_url", "")
                                }
                            }
                        ]
                except Exception:
                    pass
            formatted_messages.append({"role": m.role, "content": content})

        return {
            "model": config.model or self.default_model,
            "messages": formatted_messages,
            "temperature": config.temperature,
            "max_tokens": config.max_tokens,
            "top_p": config.top_p,
            "stop": config.stop_sequences,
        }

    _request_interval: ClassVar[float] = 2.5

    async def _request_with_retry(
        self, client: httpx.AsyncClient, payload: dict
    ) -> httpx.Response:
        loop = asyncio.get_running_loop()
        lock_key = (self.api_base or "__default__", id(loop))
        if lock_key not in self._base_locks:
            self._base_locks[lock_key] = asyncio.Lock()
        lock = self._base_locks[lock_key]

        for attempt in range(self._max_retries):
            now = time.monotonic()
            last = self._last_request.get(lock_key, 0.0)
            since_last = now - last
            if since_last < self._request_interval:
                await asyncio.sleep(self._request_interval - since_last)
            async with lock:
                now = time.monotonic()
                last = self._last_request.get(lock_key, 0.0)
                since_last = now - last
                if since_last < self._request_interval:
                    await asyncio.sleep(self._request_interval - since_last)
                resp = await client.post(
                    f"{self.api_base}/chat/completions",
                    headers=self._build_headers(),
                    json=payload,
                )
                if resp.status_code not in (429, 413):
                    self._last_request[lock_key] = time.monotonic()
            if resp.status_code in (429, 413):
                if attempt < self._max_retries - 1:
                    delay = 5 * (2 ** attempt)
                    await asyncio.sleep(delay)
                    continue
                raise ValueError(
                    f"LLM API rate limit exceeded after {self._max_retries} retries. "
                    f"Try again later or use a different provider."
                )
            return resp
        resp.raise_for_status()
        return resp

    async def generate(
        self,
        messages: list[Message],
        config: LLMConfig,
    ) -> LLMResponse:
        payload = self._build_payload(messages, config)
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await self._request_with_retry(client, payload)
            data = resp.json()
            if "choices" not in data:
                raise ValueError(f"LLM API Error (status {resp.status_code}): {data}")

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
