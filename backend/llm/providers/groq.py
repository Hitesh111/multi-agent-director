from .deepseek import DeepSeekProvider


class GroqProvider(DeepSeekProvider):
    """Groq API provider.

    Shares DeepSeek's OpenAI-compatible implementation but with fewer
    retries — Groq's 30 RPM limit means we should fail fast and let
    the quota router pick an alternative provider.
    """

    def __init__(self, config: dict):
        config = {**config, "max_retries": 2}
        super().__init__(config)
