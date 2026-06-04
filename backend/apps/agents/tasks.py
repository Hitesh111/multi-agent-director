import logging
from datetime import datetime, timedelta

from config.celery import app as celery_app

logger = logging.getLogger(__name__)


def _matches_cron(cron_expr: str, now: datetime) -> bool:
    parts = cron_expr.strip().split()
    if len(parts) < 5:
        return False
    minute, hour = parts[0], parts[1]
    minute_match = minute == "*" or str(now.minute) == minute
    hour_match = hour == "*" or str(now.hour) == hour
    return minute_match and hour_match


@celery_app.task
def check_agent_schedules():
    from .models import Agent
    from apps.executions.models import Execution
    from apps.workflows.models import Workflow
    from runtime.executor import execute_workflow

    now = datetime.now()
    triggered = 0

    for agent in Agent.objects.filter(
        schedule_config__isnull=False,
        is_active=True,
    ).exclude(schedule_config={}):
        cfg = agent.schedule_config
        if not isinstance(cfg, dict):
            continue

        should_fire = False

        interval = cfg.get("interval_minutes")
        if interval:
            last_fired = cfg.get("last_fired_at")
            if last_fired:
                try:
                    last_dt = datetime.fromisoformat(last_fired) if isinstance(last_fired, str) else datetime.fromtimestamp(last_fired)
                    if now - last_dt < timedelta(minutes=int(interval)):
                        continue
                except (ValueError, TypeError):
                    pass
            should_fire = True

        cron = cfg.get("cron")
        if cron:
            if not should_fire:
                should_fire = _matches_cron(cron, now)

        if not should_fire:
            continue

        workflows = Workflow.objects.filter(is_active=True)
        for wf in workflows:
            for node in wf.nodes or []:
                if node.get("agentId") == agent.id:
                    execution = Execution.objects.create(
                        workflow=wf,
                        status="pending",
                        input_data={"text": f"Scheduled run: {agent.name}", "source": "schedule"},
                    )
                    execute_workflow.delay(execution.id)
                    triggered += 1
                    break

        cfg["last_fired_at"] = now.isoformat()
        Agent.objects.filter(id=agent.id).update(schedule_config=cfg)

    if triggered:
        logger.info("Agent scheduler triggered %d execution(s)", triggered)
    return triggered
