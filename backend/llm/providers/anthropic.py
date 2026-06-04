import json
from typing import AsyncIterator

import httpx

from ..base import BaseLLMProvider
from ..schemas import LLMConfig, LLMResponse, EmbeddingResponse, Message, TokenUsage


class AnthropicProvider(BaseLLMProvider):
    """Anthropic Claude API provider.

    Uses the Anthropic API at api.anthropic.com/v1.
    Supports Claude 3.5 Haiku, Claude 3.5 Sonnet, Claude 3 Opus, and all
    Claude models. Uses x-api-key header authentication.
    """

    def __init__(self, config: dict):
        super().__init__(config)
        self.api_version = config.get("api_version", "2023-06-01")

    def _build_headers(self) -> dict:
        return {
            "x-api-key": self.api_key,
            "anthropic-version": self.api_version,
            "Content-Type": "application/json",
        }

    def _convert_messages(self, messages: list[Message]) -> tuple[str, list[dict]]:
        system_text = ""
        converted = []

        for m in messages:
            if m.role == "system":
                system_text += m.content + "\n"
            elif m.role == "user":
                content = m.content
                if isinstance(content, str) and content.startswith('{"type": "multimodal"'):
                    try:
                        parsed = json.loads(content)
                        blocks = [{"type": "text", "text": parsed.get("text", "")}]
                        image_url = parsed.get("image_url", "")
                        if image_url and image_url.startswith("data:"):
                            import base64
                            mime_type = image_url.split(";")[0].split(":")[1]
                            _, encoded = image_url.split(",", 1)
                            blocks.append({
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": mime_type,
                                    "data": encoded.strip(),
                                },
                            })
                        converted.append({"role": "user", "content": blocks})
                    except Exception:
                        converted.append({"role": "user", "content": content})
                else:
                    converted.append({"role": "user", "content": content})
            elif m.role == "assistant":
                converted.append({"role": "assistant", "content": m.content})

        return system_text.strip(), converted

    async def generate(self, messages: list[Message], config: LLMConfig) -> LLMResponse:
        system, converted = self._convert_messages(messages)

        body = {
            "model": config.model or self.default_model,
            "max_tokens": config.max_tokens or 4096,
            "messages": converted,
        }
        if system:
            body["system"] = system
        if config.temperature is not None:
            body["temperature"] = config.temperature
        if config.stop_sequences:
            body["stop_sequences"] = config.stop_sequences

        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                f"{self.api_base}/messages",
                headers=self._build_headers(),
                json=body,
            )
            if resp.status_code == 402:
                raise ValueError(f"Anthropic API Error (status 402): {resp.json()}")
            resp.raise_for_status()
            data = resp.json()

            text = ""
            for block in data.get("content", []):
                if block.get("type") == "text":
                    text += block.get("text", "")

            usage_data = data.get("usage", {})
            usage = TokenUsage(
                prompt_tokens=usage_data.get("input_tokens", 0),
                completion_tokens=usage_data.get("output_tokens", 0),
                total_tokens=(usage_data.get("input_tokens", 0) +
                              usage_data.get("output_tokens", 0)),
            )

            return LLMResponse(
                content=text,
                usage=usage,
                model=data.get("model", config.model or self.default_model),
                finish_reason=data.get("stop_reason", ""),
                raw=data,
            )

    async def stream(self, messages: list[Message], config: LLMConfig) -> AsyncIterator[str]:
        system, converted = self._convert_messages(messages)

        body = {
            "model": config.model or self.default_model,
            "max_tokens": config.max_tokens or 4096,
            "messages": converted,
            "stream": True,
        }
        if system:
            body["system"] = system
        if config.temperature is not None:
            body["temperature"] = config.temperature

        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream(
                "POST",
                f"{self.api_base}/messages",
                headers=self._build_headers(),
                json=body,
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data_str = line[6:]
                        if data_str.strip() == "[DONE]":
                            break
                        if data_str.strip() == "[DONE]":
                            break
                        try:
                            chunk = json.loads(data_str)
                            if chunk.get("type") == "content_block_delta":
                                delta = chunk.get("delta", {})
                                if delta.get("type") == "text_delta":
                                    text = delta.get("text", "")
                                    if text:
                                        yield text
                        except (json.JSONDecodeError, KeyError):
                            pass

    async def embeddings(self, texts: list[str], model: str = "") -> EmbeddingResponse:
        raise NotImplementedError("Embeddings not supported for Anthropic Claude")
