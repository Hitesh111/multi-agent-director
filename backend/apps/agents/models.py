from django.db import models


class Agent(models.Model):
    class Provider(models.TextChoices):
        DEEPSEEK = "deepseek", "DeepSeek"
        OPENCODE = "opencode", "OpenCode"
        GROK = "grok", "Grok"
        GEMINI = "gemini", "Gemini"
        OPENAI = "openai", "OpenAI"
        ANTHROPIC = "anthropic", "Anthropic"

    name = models.CharField(max_length=128, unique=True)
    role = models.CharField(max_length=256, blank=True, default="")
    system_prompt = models.TextField(blank=True, default="")

    provider = models.CharField(
        max_length=32,
        choices=Provider.choices,
        default=Provider.DEEPSEEK,
    )
    model = models.CharField(max_length=128, blank=True, default="")

    tools = models.JSONField(default=list, blank=True)
    skills = models.JSONField(default=list, blank=True)
    memory_enabled = models.BooleanField(default=True)
    temperature = models.FloatField(default=0.7)
    max_iterations = models.IntegerField(default=10)

    schedule_config = models.JSONField(null=True, blank=True)
    interaction_rules = models.JSONField(default=dict, blank=True)
    allowed_agents = models.JSONField(default=list, blank=True)
    enabled_channels = models.JSONField(default=list, blank=True)

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.name
