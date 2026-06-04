import logging
import re
from typing import Any
from django.conf import settings
from django.utils import timezone

from asgiref.sync import sync_to_async

from llm.schemas import LLMConfig, Message as LLMMessage
from llm.registry import ProviderRegistry
from llm.image_gen import extract_prompt, generate_image
from llm.router import select_best_providers
from llm.quota import get_quota_tracker, PERMANENT_ERROR_CODES
from apps.agents.models import Agent
from apps.executions.models import Execution, ExecutionNode
from apps.history.models import Message as HistoryMessage

from .state import WorkflowState
from apps.executions.notifications import (
    notify_node_status,
    notify_message_created,
    notify_execution_failed,
)

logger = logging.getLogger(__name__)

_sa = sync_to_async

_THINK_RE = re.compile(r"<think>.*?</think>", re.DOTALL)


def clean_response(content: str) -> str:
    return _THINK_RE.sub("", content).strip()


async def agent_node_handler(state: WorkflowState, node_def: dict) -> dict:
    node_id = node_def["id"]
    execution_id = state["execution_id"]

    try:
        execution, exec_node = await _load_execution_context(execution_id, node_id)

        if exec_node.status == Execution.Status.COMPLETED:
            content = (exec_node.output_data or {}).get("content", "")
            return {
                "node_results": {node_id: content},
                "completed_nodes": [node_id],
            }

        await _mark_node_running(exec_node)

        agent_id = node_def.get("agentId") or node_def.get("data", {}).get("agentId")
        agent = await _get_agent(agent_id)

        memory_messages = await _load_agent_memory(agent) if agent.memory_enabled else None
        messages = _build_messages(agent, state, memory_messages)

        # Select providers by most remaining quota, then try in order on failure
        candidates = [agent.provider] + getattr(settings, "PROVIDER_FALLBACK_CHAIN", {}).get(agent.provider, [])
        ordered_providers = select_best_providers(candidates)
        response = None
        last_error = None

        for provider_name in ordered_providers:
            provider = ProviderRegistry.instantiate(provider_name)
            if provider is None:
                continue

            llm_config = LLMConfig(
                model=agent.model if provider_name == agent.provider else provider.default_model,
                temperature=agent.temperature,
            )

            try:
                get_quota_tracker().record_request(provider_name)
                response = await provider.generate(messages, llm_config)
                if provider_name != agent.provider:
                    logger.info("Quota router: %s used %s instead of %s", node_id, provider_name, agent.provider)
                break
            except Exception as e:
                last_error = e
                logger.warning("Provider %s failed for node %s: %s", provider_name, node_id, e)
                em = str(e)
                # Permanent failures (402, auth errors) — skip for rest of session
                for code in PERMANENT_ERROR_CODES:
                    if f"status {code}" in em:
                        get_quota_tracker().mark_dead(provider_name)
                        logger.info("Marked %s as dead (status %d)", provider_name, code)
                        break
                else:
                    # Rate-limited (429) — cooldown so other nodes don't waste time retrying
                    if "status 429" in em or "429" in em:
                        get_quota_tracker().set_cooldown(provider_name, duration=60.0)
                        logger.info("Cooldown %s for 60s (429)", provider_name)
                    # No API key / unconfigured — mark dead for rest of session
                    elif "API key not configured" in em or "not configured" in em.lower():
                        get_quota_tracker().mark_dead(provider_name)
                        logger.info("Marked %s as dead (not configured)", provider_name)
                continue

        if response is None:
            raise last_error or RuntimeError("All providers in fallback chain failed")

        response.content = clean_response(response.content) if response.content else response.content

        image_url = None
        if node_id == "image_gen" and response.content:
            prompt = extract_prompt(response.content)
            if prompt:
                image_url = await generate_image(prompt)
                if image_url:
                    response.content += f"\n\n![Scene]({image_url})"

        await _save_agent_message(execution, exec_node, agent, response)
        await _mark_node_completed(exec_node, response.content, response.usage)
        await _update_execution_tokens(execution, response.usage)

        return {
            "node_results": {node_id: response.content},
            "messages": [{"role": "assistant", "content": response.content, "node": node_id}],
            "completed_nodes": [node_id],
        }

    except Exception as e:
        logger.exception("Agent node %s failed: %s", node_id, e)
        await _mark_node_failed(execution_id, node_id, str(e))
        await _mark_execution_failed(execution_id, str(e))
        return {
            "status": "failed",
            "error": str(e),
            "completed_nodes": [node_id],
        }


async def approval_node_handler(state: WorkflowState, node_def: dict) -> dict:
    node_id = node_def["id"]
    execution_id = state["execution_id"]

    exec_node = await _get_execution_node(execution_id, node_id)

    if exec_node.status == Execution.Status.COMPLETED:
        return {"completed_nodes": [node_id], "approved": True}

    await _mark_node_needs_approval(exec_node)
    await _mark_execution_awaiting_approval(execution_id)

    return {
        "status": "needs_approval",
        "completed_nodes": [node_id],
    }


async def input_node_handler(state: WorkflowState, node_def: dict) -> dict:
    node_id = node_def["id"]
    execution_id = state["execution_id"]
    try:
        execution, exec_node = await _load_execution_context(execution_id, node_id)

        if exec_node.status == Execution.Status.COMPLETED:
            return {"completed_nodes": [node_id]}

        await _mark_node_running(exec_node)
        await _mark_node_completed(exec_node, "Input stage completed", None)
    except Exception as e:
        logger.warning("input_node_handler error for node %s: %s", node_id, e)
    return {
        "completed_nodes": [node_id],
    }


async def output_node_handler(state: WorkflowState, node_def: dict) -> dict:
    node_id = node_def["id"]
    execution_id = state["execution_id"]
    try:
        execution, exec_node = await _load_execution_context(execution_id, node_id)

        if exec_node.status == Execution.Status.COMPLETED:
            pass
        else:
            await _mark_node_running(exec_node)

    except Exception as e:
        logger.warning("output_node_handler context load failed for node %s: %s", node_id, e)

    node_results = state.get("node_results", {})
    input_data = state.get("input_data", {})

    output_parts = []

    if isinstance(input_data, dict) and "text" in input_data:
        output_parts.append(f"# Player Action\n{input_data['text']}")
    elif input_data:
        output_parts.append(f"# Input\n{input_data}")

    narrative_keys = {"narrator", "npc", "combat", "quest", "inventory", "image_gen"}
    data_keys = {"world_state", "store_memory"}

    for key in narrative_keys:
        val = node_results.get(key)
        if val:
            label = {"narrator": "Narrator", "npc": "NPC", "combat": "Combat",
                     "quest": "Quest", "inventory": "Inventory", "image_gen": "Scene Visual"}.get(key, key)
            output_parts.append(f"## {label}\n{val}")

    for key in data_keys:
        val = node_results.get(key)
        if val:
            output_parts.append(f"### {key}\n```json\n{val}\n```")

    for key, val in node_results.items():
        if key in narrative_keys | data_keys | {"input"} or not val:
            continue
        label = key.replace("_", " ").title()
        output_parts.append(f"## {label}\n{val}")

    final_output = "\n\n".join(output_parts) if output_parts else "Workflow completed."

    try:
        await _mark_node_completed(exec_node, final_output, None)
    except Exception as e:
        logger.warning("output_node_handler mark_completed failed for node %s: %s", node_id, e)

    scene_image = None
    image_gen_content = node_results.get("image_gen", "")
    if image_gen_content:
        m = re.search(r"!\[Scene\]\(([^)]+)\)", image_gen_content)
        if m:
            scene_image = m.group(1)

    output_data = {
        "content": final_output,
        "narrative": final_output,
        "node_results": dict(node_results),
        "messages": state.get("messages", []),
    }
    if scene_image:
        output_data["scene_image"] = scene_image

    return {
        "completed_nodes": [node_id],
        "output_data": output_data,
    }


def get_node_handler(node_type: str, node_def: dict):
    handlers = {
        "agent": agent_node_handler,
        "human_approval": approval_node_handler,
        "input": input_node_handler,
        "output": output_node_handler,
    }
    handler = handlers.get(node_type, agent_node_handler)

    async def wrapper(state: WorkflowState) -> dict:
        return await handler(state, node_def)

    return wrapper


async def _load_agent_memory(agent: Agent) -> list[LLMMessage]:
    from apps.history.models import Message as HistoryMessage

    past = await _sa(
        lambda: list(
            HistoryMessage.objects
            .filter(source_agent=agent)
            .exclude(role=HistoryMessage.Role.SYSTEM)
            .order_by("-created_at")[:20]
        )
    )()
    return [
        LLMMessage(role=m.role, content=m.content)
        for m in reversed(past)
    ]


def _build_messages(agent: Agent, state: WorkflowState, memory_messages: list[LLMMessage] | None = None) -> list[LLMMessage]:
    messages = []

    # Build combined system prompt from agent prompt + skills
    system_parts = []
    if agent.system_prompt:
        system_parts.append(agent.system_prompt)
    if agent.skills:
        system_parts.append(f"You have the following skills: {', '.join(agent.skills)}")
    if system_parts:
        messages.append(LLMMessage(role="system", content="\n\n".join(system_parts)))

    # Enforce guardrails from interaction_rules
    rules = agent.interaction_rules or {}
    if rules.get("max_turns") and memory_messages:
        turn_count = len([m for m in memory_messages if m.role == "user"]) + 1
        if turn_count > int(rules["max_turns"]):
            raise RuntimeError(f"Conversation exceeded max_turns limit ({rules['max_turns']})")
    if rules.get("max_response_length"):
        messages.append(
            LLMMessage(role="system", content=f"Keep responses under {int(rules['max_response_length'])} characters.")
        )
    if rules.get("allowed_topics"):
        topics = rules["allowed_topics"]
        if isinstance(topics, list):
            messages.append(
                LLMMessage(role="system", content=f"You are only allowed to discuss: {', '.join(topics)}")
            )

    # Include persistent memory (past conversations) if available
    if memory_messages:
        messages.append(
            LLMMessage(role="system", content=f"Previous conversation:\n" + "\n".join(f"{m.role}: {m.content[:2000]}" for m in memory_messages[-10:]))
        )

    # Include previous node results as context
    node_results = state.get("node_results", {})
    context_parts = []
    if node_results:
        for node_id, output in node_results.items():
            if output:
                context_parts.append(f"[{node_id} output]:\n{output[:2000]}")
    if context_parts:
        messages.append(
            LLMMessage(role="system", content="Previous pipeline results:\n" + "\n\n".join(context_parts))
        )

    for msg in state.get("messages", []):
        messages.append(LLMMessage(role=msg.get("role", "user"), content=msg.get("content", "")))
    if state.get("input_data"):
        input_data = state["input_data"]
        if isinstance(input_data, dict) and "image_url" in input_data:
            import json
            prompt = input_data.get("text") or "Analyze this image and describe it, extracting all readable text."
            payload = {
                "type": "multimodal",
                "text": prompt,
                "image_url": input_data["image_url"]
            }
            messages.append(
                LLMMessage(role="user", content=json.dumps(payload))
            )
        else:
            messages.append(
                LLMMessage(role="user", content=f"Input: {state['input_data']}")
            )
    return messages


async def _load_execution_context(execution_id: int, node_id: str):
    return await _sa(
        lambda: (
            Execution.objects.get(id=execution_id),
            ExecutionNode.objects.get(execution_id=execution_id, node_id=node_id),
        )
    )()


async def _get_execution_node(execution_id: int, node_id: str) -> ExecutionNode:
    return await _sa(lambda: ExecutionNode.objects.get(execution_id=execution_id, node_id=node_id))()


async def _get_agent(agent_id: int) -> Agent:
    return await _sa(lambda: Agent.objects.get(id=agent_id))()


async def _mark_node_running(exec_node):
    await _sa(
        lambda: ExecutionNode.objects.filter(id=exec_node.id).update(
            status=Execution.Status.RUNNING,
            started_at=timezone.now(),
        )
    )()
    await notify_node_status(exec_node.execution_id, exec_node.node_id, "running")


async def _mark_node_completed(exec_node, output: str, usage):
    await _sa(
        lambda: ExecutionNode.objects.filter(id=exec_node.id).update(
            status=Execution.Status.COMPLETED,
            output_data={"content": output},
            completed_at=timezone.now(),
        )
    )()
    await notify_node_status(
        exec_node.execution_id, exec_node.node_id, "completed",
        output_preview=output[:200] if output else "",
        total_tokens=usage.total_tokens if usage else 0,
    )


async def _mark_node_needs_approval(exec_node):
    await _sa(
        lambda: ExecutionNode.objects.filter(id=exec_node.id).update(
            status=Execution.Status.NEEDS_APPROVAL,
            started_at=timezone.now(),
        )
    )()
    await notify_node_status(exec_node.execution_id, exec_node.node_id, "needs_approval")


async def _mark_node_failed(execution_id: int, node_id: str, error: str):
    await _sa(
        lambda: ExecutionNode.objects.filter(
            execution_id=execution_id, node_id=node_id
        ).update(
            status=Execution.Status.FAILED,
            error_message=error,
            completed_at=timezone.now(),
        )
    )()
    await notify_node_status(execution_id, node_id, "failed", error=error)


async def _mark_execution_failed(execution_id: int, error: str):
    await _sa(
        lambda: Execution.objects.filter(id=execution_id).update(
            status=Execution.Status.FAILED,
            error_message=error,
            completed_at=timezone.now(),
        )
    )()
    await notify_execution_failed(execution_id, error)


async def _mark_execution_awaiting_approval(execution_id: int):
    await _sa(
        lambda: Execution.objects.filter(id=execution_id).update(
            status=Execution.Status.NEEDS_APPROVAL,
        )
    )()


async def _save_agent_message(
    execution: Execution, exec_node: ExecutionNode, agent: Agent, response
):
    await _sa(
        lambda: HistoryMessage.objects.create(
            execution=execution,
            execution_node=exec_node,
            source_agent=agent,
            role=HistoryMessage.Role.ASSISTANT,
            content=response.content,
            token_count=response.usage.total_tokens,
            metadata={
                "model": response.model,
                "finish_reason": response.finish_reason,
            },
        )
    )()
    await notify_message_created(
        execution_id=execution.id,
        node_id=exec_node.node_id,
        agent_name=agent.name,
        role="assistant",
        content=response.content,
        token_count=response.usage.total_tokens,
    )


async def _update_execution_tokens(execution: Execution, usage):
    await _sa(
        lambda: _do_update_tokens(execution, usage)
    )()


def _do_update_tokens(execution: Execution, usage):
    current = dict(execution.token_usage or {})
    current["prompt_tokens"] = current.get("prompt_tokens", 0) + usage.prompt_tokens
    current["completion_tokens"] = current.get("completion_tokens", 0) + usage.completion_tokens
    current["total_tokens"] = current.get("total_tokens", 0) + usage.total_tokens
    Execution.objects.filter(id=execution.id).update(token_usage=current)
