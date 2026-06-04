from typing import Optional

from django.conf import settings

from .base import BaseLLMProvider
from .providers.deepseek import DeepSeekProvider
from .providers.groq import GroqProvider
from .providers.opencode import OpenCodeProvider
from .providers.openai import OpenAIProvider
from .providers.gemini import GeminiProvider
from .providers.anthropic import AnthropicProvider


class ProviderRegistry:
    """Registry that maps provider names to implementations.

    New providers register themselves here. Agents select a provider
    by name stored in DB config — the registry resolves it at runtime.
    """

    _providers: dict[str, type[BaseLLMProvider]] = {}

    @classmethod
    def register(cls, name: str, provider_cls: type[BaseLLMProvider]) -> None:
        cls._providers[name] = provider_cls

    @classmethod
    def get(cls, name: str) -> Optional[type[BaseLLMProvider]]:
        return cls._providers.get(name)

    @classmethod
    def list_providers(cls) -> list[str]:
        return list(cls._providers.keys())

    @classmethod
    def instantiate(cls, name: str) -> Optional[BaseLLMProvider]:
        provider_cls = cls.get(name)
        if provider_cls is None:
            return None
        provider_config = settings.LLM_PROVIDERS.get(name, {})
        return provider_cls(provider_config)


ProviderRegistry.register("deepseek", DeepSeekProvider)
ProviderRegistry.register("opencode", OpenCodeProvider)
ProviderRegistry.register("grok", GroqProvider)
ProviderRegistry.register("gemini", GeminiProvider)
ProviderRegistry.register("openai", OpenAIProvider)
ProviderRegistry.register("anthropic", AnthropicProvider)
