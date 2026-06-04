from django.db import models


class Workflow(models.Model):
    name = models.CharField(max_length=128, unique=True)
    description = models.TextField(blank=True, default="")

    nodes = models.JSONField(default=list)
    edges = models.JSONField(default=list)

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.name
