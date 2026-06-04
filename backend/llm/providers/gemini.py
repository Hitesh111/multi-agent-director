import asyncio
import json
import time
from typing import AsyncIterator, ClassVar

import httpx

from ..base import BaseLLMProvider
from ..schemas import LLMConfig, LLMResponse, EmbeddingResponse, Message, TokenUsage


class GeminiProvider(BaseLLMProvider):
    """Google Gemini API provider.

    Uses the Google AI Gemini API at generativelanguage.googleapis.com.
    Supports Gemini 1.5 Pro, Gemini 1.5 Flash, Gemini 2.0 Flash, and all
    Gemini models. The API key is passed as a query parameter.
    """

    _base_locks: ClassVar[dict[tuple, asyncio.Lock]] = {}
    _request_interval: ClassVar[float] = 10.0
    _last_request: ClassVar[dict[tuple, float]] = {}

    def __init__(self, config: dict):
        super().__init__(config)
        self.api_base = config.get("api_base", "https://generativelanguage.googleapis.com/v1beta")
        self.api_key = config.get("api_key", "")

    def _build_url(self, model: str, method: str = "generateContent") -> str:
        return f"{self.api_base}/models/{model}:{method}?key={self.api_key}"

    async def _request_with_retry(self, client: httpx.AsyncClient, url: str, body: dict) -> httpx.Response:
        loop = asyncio.get_running_loop()
        lock_key = (self.api_base or "__default__", id(loop))
        if lock_key not in self._base_locks:
            self._base_locks[lock_key] = asyncio.Lock()
        lock = self._base_locks[lock_key]

        max_retries = 2
        for attempt in range(max_retries):
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
                resp = await client.post(url, json=body)
                if resp.status_code != 429:
                    self._last_request[lock_key] = time.monotonic()
            if resp.status_code == 429:
                if attempt < max_retries - 1:
                    wait = 5 + attempt * 5
                    await asyncio.sleep(wait)
                    continue
                resp.raise_for_status()
                return resp
            return resp
        resp.raise_for_status()
        return resp

    def _convert_messages(self, messages: list[Message]) -> dict:
        system_prompt = ""
        contents = []

        for m in messages:
            if m.role == "system":
                system_prompt += m.content + "\n"
            elif m.role == "user":
                content = m.content
                if isinstance(content, str) and content.startswith('{"type": "multimodal"'):
                    try:
                        parsed = json.loads(content)
                        parts = [{"text": parsed.get("text", "")}]
                        image_url = parsed.get("image_url", "")
                        if image_url:
                            if image_url.startswith("data:"):
                                import base64
                                _, encoded = image_url.split(",", 1)
                                parts.append({
                                    "inlineData": {
                                        "mimeType": "image/jpeg",
                                        "data": encoded.strip(),
                                    }
                                })
                            else:
                                parts.append({"text": f"[Image URL: {image_url}]"})
                        contents.append({"role": "user", "parts": parts})
                    except Exception:
                        contents.append({"role": "user", "parts": [{"text": content}]})
                else:
                    contents.append({"role": "user", "parts": [{"text": content}]})
            elif m.role == "assistant":
                contents.append({"role": "model", "parts": [{"text": m.content}]})

        result = {"contents": contents}
        if system_prompt:
            result["systemInstruction"] = {"parts": [{"text": system_prompt.strip()}]}

        return result

    def _build_config(self, config: LLMConfig) -> dict:
        gen_config = {}
        if config.temperature is not None:
            gen_config["temperature"] = config.temperature
        if config.max_tokens:
            gen_config["maxOutputTokens"] = config.max_tokens
        if config.top_p is not None:
            gen_config["topP"] = config.top_p
        if config.stop_sequences:
            gen_config["stopSequences"] = config.stop_sequences
        return gen_config

    async def generate(self, messages: list[Message], config: LLMConfig) -> LLMResponse:
        body = self._convert_messages(messages)
        gen_config = self._build_config(config)
        if gen_config:
            body["generationConfig"] = gen_config

        model = config.model or self.default_model
        url = self._build_url(model)

        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await self._request_with_retry(client, url, body)
            if resp.status_code == 402:
                raise ValueError(f"Gemini API Error (status 402): {resp.json()}")
            if resp.status_code == 403:
                error_data = resp.json()
                msg = error_data.get("error", {}).get("message", str(error_data))
                if "API_KEY" in msg or "key" in msg.lower():
                    raise ValueError(f"Gemini API key error: {msg}")
                raise ValueError(f"Gemini API Error (status 403): {msg}")
            data = resp.json()

            candidate = data.get("candidates", [{}])[0]
            content_parts = candidate.get("content", {}).get("parts", [{}])
            text = "".join(p.get("text", "") for p in content_parts)

            usage_data = data.get("usageMetadata", {})
            usage = TokenUsage(
                prompt_tokens=usage_data.get("promptTokenCount", 0),
                completion_tokens=usage_data.get("candidatesTokenCount", 0),
                total_tokens=usage_data.get("totalTokenCount", 0),
            )

            finish_reason = candidate.get("finishReason", "")

            return LLMResponse(
                content=text,
                usage=usage,
                model=data.get("model", model),
                finish_reason=finish_reason,
                raw=data,
            )

    async def stream(self, messages: list[Message], config: LLMConfig) -> AsyncIterator[str]:
        body = self._convert_messages(messages)
        gen_config = self._build_config(config)
        if gen_config:
            body["generationConfig"] = gen_config

        model = config.model or self.default_model
        url = self._build_url(model, "streamGenerateContent")

        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream("POST", url, json=body) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data_str = line[6:]
                        if data_str.strip() == "[DONE]":
                            break
                        try:
                            chunk = json.loads(data_str)
                            parts = chunk.get("candidates", [{}])[0].get("content", {}).get("parts", [])
                            for p in parts:
                                text = p.get("text", "")
                                if text:
                                    yield text
                        except (json.JSONDecodeError, IndexError):
                            pass

    async def embeddings(self, texts: list[str], model: str = "") -> EmbeddingResponse:
        model = model or self.default_model
        url = self._build_url(model, "batchEmbedContents")

        body = {
            "requests": [
                {"model": f"models/{model}", "content": {"parts": [{"text": t}]}}
                for t in texts
            ]
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(url, json=body)
            resp.raise_for_status()
            data = resp.json()

            embeddings_list = [
                e["values"] for e in data.get("embeddings", [])
            ]

            return EmbeddingResponse(
                embeddings=embeddings_list,
                model=model,
                usage=TokenUsage(),
            )
