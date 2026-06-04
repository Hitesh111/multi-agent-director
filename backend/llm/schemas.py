from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Message:
    role: str  # "system" | "user" | "assistant" | "tool"
    content: str
    name: Optional[str] = None
    tool_call_id: Optional[str] = None
    tool_calls: Optional[list[dict]] = None


@dataclass
class LLMConfig:
    model: str
    temperature: float = 0.7
    max_tokens: int = 4096
    top_p: float = 0.9
    stop_sequences: Optional[list[str]] = None


@dataclass
class TokenUsage:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


@dataclass
class LLMResponse:
    content: str
    usage: TokenUsage = field(default_factory=TokenUsage)
    model: str = ""
    finish_reason: str = ""
    raw: Optional[dict] = None


@dataclass
class EmbeddingResponse:
    embeddings: list[list[float]]
    model: str = ""
    usage: TokenUsage = field(default_factory=TokenUsage)
