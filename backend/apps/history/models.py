from django.db import models


class Message(models.Model):
    class Role(models.TextChoices):
        SYSTEM = "system", "System"
        USER = "user", "User"
        ASSISTANT = "assistant", "Assistant"
        TOOL = "tool", "Tool"

    execution = models.ForeignKey(
        "executions.Execution",
        on_delete=models.CASCADE,
        related_name="messages",
        null=True,
        blank=True,
    )
    execution_node = models.ForeignKey(
        "executions.ExecutionNode",
        on_delete=models.CASCADE,
        related_name="messages",
        null=True,
        blank=True,
    )
    source_agent = models.ForeignKey(
        "agents.Agent",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sent_messages",
    )
    target_agent = models.ForeignKey(
        "agents.Agent",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="received_messages",
    )
    role = models.CharField(max_length=16, choices=Role.choices)
    content = models.TextField()
    metadata = models.JSONField(default=dict, blank=True)
    token_count = models.IntegerField(default=0)
    channel = models.CharField(max_length=64, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"Message {self.id} [{self.role}] via {self.channel or 'internal'}"
