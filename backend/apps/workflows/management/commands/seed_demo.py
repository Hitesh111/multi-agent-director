import logging

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.agents.models import Agent
from apps.workflows.models import Workflow

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Seed the database with demo agents and a Research→Summarizer→Reviewer workflow"

    def handle(self, *args, **options):
        self.stdout.write("Seeding demo data...")

        with transaction.atomic():
            self._create_agents()
            self._create_workflow()

        self.stdout.write(self.style.SUCCESS("Demo data seeded successfully!"))
        self.stdout.write("  Agents: ResearchAgent, SummarizerAgent, ReviewerAgent, CodeWriterAgent, CodeReviewerAgent, ImageAnalyzerAgent, DraftWriterAgent")
        self.stdout.write("  Workflows: Research → Summarize → Review, Code Writer → Code Reviewer, Image Analyzer, Draft & Approve")

    def _create_agents(self):
        research, created = Agent.objects.update_or_create(
            name="ResearchAgent",
            defaults={
                "role": "Research specialist",
                "system_prompt": (
                    "You are a research specialist. Your job is to find and organize "
                    "information about any given topic. Be thorough, cite key facts, "
                    "and structure your findings clearly. Output a well-organized research brief."
                ),
                "provider": Agent.Provider.DEEPSEEK,
                "temperature": 0.7,
                "max_iterations": 3,
                "memory_enabled": True,
            },
        )
        self.stdout.write(f"  {'Created' if created else 'Updated'}: {research.name}")

        summarizer, created = Agent.objects.update_or_create(
            name="SummarizerAgent",
            defaults={
                "role": "Content summarizer",
                "system_prompt": (
                    "You are a summarization expert. Take the research findings provided "
                    "and distill them into a concise, well-structured summary. "
                    "Preserve key facts and insights. Aim for 3-5 paragraphs."
                ),
                "provider": Agent.Provider.DEEPSEEK,
                "temperature": 0.5,
                "max_iterations": 3,
                "memory_enabled": True,
            },
        )
        self.stdout.write(f"  {'Created' if created else 'Updated'}: {summarizer.name}")

        reviewer, created = Agent.objects.update_or_create(
            name="ReviewerAgent",
            defaults={
                "role": "Quality reviewer",
                "system_prompt": (
                    "You are a quality assurance reviewer. Review the summary provided, "
                    "check for accuracy, clarity, and completeness. Provide a final polished "
                    "version along with brief feedback on quality (rating 1-10). "
                    "Output format:\n\n"
                    "Quality Score: X/10\n"
                    "Feedback: ...\n"
                    "Final Output:\n"
                    "..."
                ),
                "provider": Agent.Provider.DEEPSEEK,
                "temperature": 0.4,
                "max_iterations": 3,
                "memory_enabled": True,
                "enabled_channels": ["telegram"],
            },
        )
        self.stdout.write(f"  {'Created' if created else 'Updated'}: {reviewer.name}")

        writer, created = Agent.objects.update_or_create(
            name="CodeWriterAgent",
            defaults={
                "role": "Software developer",
                "system_prompt": (
                    "You are an expert software developer. Write clean, robust, "
                    "and well-commented code in the requested language to solve the problem. "
                    "Focus on readability and edge cases."
                ),
                "provider": Agent.Provider.DEEPSEEK,
                "temperature": 0.5,
                "max_iterations": 3,
                "memory_enabled": True,
            },
        )
        self.stdout.write(f"  {'Created' if created else 'Updated'}: {writer.name}")
        critic, created = Agent.objects.update_or_create(
            name="CodeReviewerAgent",
            defaults={
                "role": "Senior code reviewer",
                "system_prompt": (
                    "You are a senior code reviewer. Review the provided code for "
                    "correctness, security, performance, and style. Suggest improvements "
                    "and output the final verified code."
                ),
                "provider": Agent.Provider.DEEPSEEK,
                "temperature": 0.3,
                "max_iterations": 3,
                "memory_enabled": True,
            },
        )
        self.stdout.write(f"  {'Created' if created else 'Updated'}: {critic.name}")

        image_analyzer, created = Agent.objects.update_or_create(
            name="ImageAnalyzerAgent",
            defaults={
                "role": "Image analysis and OCR specialist",
                "system_prompt": (
                    "You are a structured image analysis and OCR specialist. Analyze the input image and provide a comprehensive structured output:\n"
                    "1. **Visual Description**: A detailed explanation of all visual components, objects, layout, and colors.\n"
                    "2. **Extracted Text**: A precise, verbatim extraction of all readable text within the image.\n\n"
                    "Be thorough, exact, and format your output beautifully in Markdown."
                ),
                "provider": Agent.Provider.GROK,
                "model": "meta-llama/llama-4-scout-17b-16e-instruct",
                "temperature": 0.3,
                "max_iterations": 3,
                "memory_enabled": True,
            },
        )
        self.stdout.write(f"  {'Created' if created else 'Updated'}: {image_analyzer.name}")

        draft_writer, created = Agent.objects.update_or_create(
            name="DraftWriterAgent",
            defaults={
                "role": "Content drafter",
                "system_prompt": (
                    "You are a content drafter. Given a topic or prompt, write a "
                    "well-structured draft. Use clear headings, concise paragraphs, "
                    "and include key points in a logical flow. The draft will be "
                    "reviewed by a human before final publication."
                ),
                "provider": Agent.Provider.DEEPSEEK,
                "temperature": 0.6,
                "max_iterations": 3,
                "memory_enabled": True,
            },
        )
        self.stdout.write(f"  {'Created' if created else 'Updated'}: {draft_writer.name}")

    def _create_workflow(self):
        research = Agent.objects.get(name="ResearchAgent")
        summarizer = Agent.objects.get(name="SummarizerAgent")
        reviewer = Agent.objects.get(name="ReviewerAgent")

        wf, created = Workflow.objects.update_or_create(
            name="Research → Summarize → Review",
            defaults={
                "description": (
                    "A complete research pipeline: an agent researches the topic, "
                    "a second agent summarizes the findings, and a third agent reviews "
                    "the final output for quality."
                ),
                "nodes": [
                    {
                        "id": "research",
                        "type": "agent",
                        "agentId": research.id,
                        "data": {"agentId": research.id},
                    },
                    {
                        "id": "summarize",
                        "type": "agent",
                        "agentId": summarizer.id,
                        "data": {"agentId": summarizer.id},
                    },
                    {
                        "id": "review",
                        "type": "agent",
                        "agentId": reviewer.id,
                        "data": {"agentId": reviewer.id},
                    },
                ],
                "edges": [
                    {"source": "research", "target": "summarize"},
                    {"source": "summarize", "target": "review"},
                ],
                "is_active": True,
            },
        )
        self.stdout.write(f"  {'Created' if created else 'Updated'}: {wf.name}")

        writer = Agent.objects.get(name="CodeWriterAgent")
        critic = Agent.objects.get(name="CodeReviewerAgent")

        code_wf, created = Workflow.objects.update_or_create(
            name="Code Writer → Code Reviewer",
            defaults={
                "description": (
                    "Develop code: an agent writes the code based on requirements, "
                    "and a senior reviewer analyzes it, optimizes it, and produces "
                    "the final verified solution."
                ),
                "nodes": [
                    {
                        "id": "write",
                        "type": "agent",
                        "agentId": writer.id,
                        "data": {"agentId": writer.id},
                    },
                    {
                        "id": "review",
                        "type": "agent",
                        "agentId": critic.id,
                        "data": {"agentId": critic.id},
                    },
                ],
                "edges": [
                    {"source": "write", "target": "review"},
                ],
                "is_active": True,
            },
        )
        self.stdout.write(f"  {'Created' if created else 'Updated'}: {code_wf.name}")

        analyzer = Agent.objects.get(name="ImageAnalyzerAgent")
        vision_wf, created = Workflow.objects.update_or_create(
            name="Image Analyzer",
            defaults={
                "description": (
                    "Analyze images: an AI vision specialist describes the visual content "
                    "and extracts all text in a structured format."
                ),
                "nodes": [
                    {
                        "id": "image_analyze",
                        "type": "agent",
                        "agentId": analyzer.id,
                        "data": {"agentId": analyzer.id},
                    },
                ],
                "edges": [],
                "is_active": True,
            },
        )
        self.stdout.write(f"  {'Created' if created else 'Updated'}: {vision_wf.name}")

        draft_writer = Agent.objects.get(name="DraftWriterAgent")
        approve_wf, created = Workflow.objects.update_or_create(
            name="Draft & Approve",
            defaults={
                "description": (
                    "A human-in-the-loop workflow: an AI drafts content, "
                    "then pauses for human approval before producing the final output."
                ),
                "nodes": [
                    {
                        "id": "input",
                        "type": "input",
                        "data": {},
                    },
                    {
                        "id": "draft",
                        "type": "agent",
                        "agentId": draft_writer.id,
                        "data": {"agentId": draft_writer.id},
                    },
                    {
                        "id": "approve",
                        "type": "human_approval",
                        "data": {},
                    },
                    {
                        "id": "output",
                        "type": "output",
                        "data": {},
                    },
                ],
                "edges": [
                    {"source": "input", "target": "draft"},
                    {"source": "draft", "target": "approve"},
                    {"source": "approve", "target": "output"},
                ],
                "is_active": True,
            },
        )
        self.stdout.write(f"  {'Created' if created else 'Updated'}: {approve_wf.name}")
