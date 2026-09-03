"""
CAR-bench Agent - Agent under test that solves CAR-bench tasks.

This is the agent being tested. It:
1. Receives task descriptions with available tools from the evaluator
2. Decides which tool to call or how to respond
3. Returns responses in the expected JSON format wrapped in <json>...</json> tags
"""
import argparse
import copy
import json
import os
import re
import time
from pathlib import Path
import sys
import uvicorn
from dotenv import load_dotenv

load_dotenv()

from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.tasks import TaskUpdater
from a2a.helpers.proto_helpers import new_message, new_text_part, new_data_part, new_task_from_user_message
from a2a.types import Role, TaskState
from google.protobuf.json_format import MessageToDict
import litellm
litellm.suppress_debug_info = True

from litellm import completion
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).parent.parent))
from logging_utils import configure_logger
from tool_call_types import ToolCall, ToolCallsData
from turn_metrics import TURN_METRICS_KEY, PROMPT_TOKENS, COMPLETION_TOKENS, COST, MODEL, THINKING_TOKENS, NUM_LLM_CALLS, AVG_LLM_CALL_TIME_MS, NUM_PASSES
sys.path.pop(0)

logger = configure_logger(role="agent_under_test", context="-")

SYSTEM_PROMPT = """You are a helpful car voice assistant. Follow the policy and tool instructions provided."""
SELECTED_SKILLS_METADATA_KEY = "selected_skill_names"
SELECTED_SKILLS_PATH_METADATA_KEY = "selected_skill_paths"
SELECTED_SKILLS_SOURCE_METADATA_KEY = "selected_skill_source"
SKILL_INJECTION_LOCATION = "system_prompt"

SKILL_SELECTION_SYSTEM_TEMPLATE = """You select operation guide skills for a CAR-bench in-car voice assistant.

Return ONLY a JSON object with this shape:
{{"skills": ["skill-name"]}}

Rules:
- Choose 0 to 5 skills from the available skill names exactly as written.
- Prefer exactly one skill when the request maps to a single operation.
- Choose multiple skills when the current user request genuinely spans multiple operations.
- Choose [] only for general conversation or a request that none of the skills cover.
- Do not answer the user, do not call tools, and do not include explanations.
- Infer the skill from the ongoing operation and prior user request.

Available skills:
{skill_index}
"""

SKILL_CONTEXT_HEADER = """# Relevant CAR Assistant Skills for Guidance

CRITICAL: Never claim or imply that a task is done unless you have actually taken some actions to finish it.

CRITICAL: Skills may mention tools or tool parameters (arguments) that do NOT exist in the current tool set. The tool schemas provided to you are the single source of truth. Before calling any tool, verify it exists in your current tool list, and pass ONLY the parameters defined in its actual schema. If a skill references a tool that is not in your available tools, do NOT call it — inform the user the capability is unavailable. If a skill references a parameter, field, or argument that is not in the tool's real schema, do NOT include it — follow the schema.

Use these operating guides before answering the user or choosing tool calls. The system prompt and the actual tool schemas/results still take precedence. Do not mention skill names unless the user asks.
"""

DEFAULT_SKILLS_BANK_DIR = Path(__file__).resolve().parents[2] / "skills_bank"

RESPONSES_STATE_MODES = {"stateless", "provider-default"}


def _completion_kwargs(
    *,
    model: str,
    tools: list[dict],
    temperature: float | None,
    thinking: bool,
    reasoning_effort: str | None,
    interleaved_thinking: bool,
    api_mode: str = "chat",
    responses_state_mode: str = "stateless",
) -> dict:
    """Build provider kwargs while keeping baseline settings narrowly scoped."""
    if responses_state_mode not in RESPONSES_STATE_MODES:
        raise ValueError(
            "responses_state_mode must be 'stateless' or 'provider-default'"
        )

    if api_mode == "responses":
        if model.startswith(("azure/responses/", "openai/responses/", "responses/")):
            request_model = model
        elif model.startswith(("azure/", "openai/")):
            provider, deployment = model.split("/", 1)
            request_model = f"{provider}/responses/{deployment}"
        else:
            request_model = f"openai/responses/{model}"
    elif api_mode == "chat":
        request_model = model
    else:
        raise ValueError("api_mode must be 'chat' or 'responses'")

    kwargs = {
        "model": request_model,
        "tools": tools if tools else None,
    }

    if api_mode == "responses" and responses_state_mode == "stateless":
        # Portable encrypted reasoning avoids relying on Azure's server-side
        # rs_* item lookup when replaying tool-call history.
        kwargs["store"] = False
        kwargs["include"] = ["reasoning.encrypted_content"]

    if temperature is not None:
        kwargs["temperature"] = temperature

    # GPT-5.6 Sol's default reasoning mode is incompatible with function tools
    # on Chat Completions. The baseline intentionally retains Chat Completions,
    # so disable reasoning only for this otherwise-invalid combination.
    normalized_model = model.removeprefix("openai/").removeprefix("azure/")
    if api_mode == "chat" and tools and normalized_model == "gpt-5.6-sol":
        kwargs["reasoning_effort"] = "none"

    if thinking:
        if model == "claude-opus-4-6":
            kwargs["thinking"] = {"type": "adaptive"}
        elif reasoning_effort is not None:
            if reasoning_effort in [
                "none",
                "disable",
                "low",
                "medium",
                "high",
            ]:
                kwargs["reasoning_effort"] = reasoning_effort
            else:
                try:
                    thinking_budget = int(reasoning_effort)
                except ValueError:
                    raise ValueError(
                        "reasoning_effort must be 'none', 'disable', 'low', "
                        "'medium', 'high', or an integer value"
                    )
                kwargs["thinking"] = {
                    "type": "enabled",
                    "budget_tokens": thinking_budget,
                }

        if interleaved_thinking:
            kwargs["extra_headers"] = {
                "anthropic-beta": "interleaved-thinking-2025-05-14"
            }

    return kwargs


def _assistant_content(response) -> dict:
    """Merge Responses-bridge output items into one Chat-style assistant message."""
    messages = [
        choice.message.model_dump(exclude_unset=True)
        for choice in response.choices
    ]
    if not messages:
        raise ValueError("LLM response contained no choices")

    merged = dict(messages[0])
    for key in ("tool_calls", "reasoning_items", "thinking_blocks"):
        values = [item for message in messages for item in (message.get(key) or [])]
        if values:
            merged[key] = values
    for key in ("content", "reasoning_content"):
        values = [message.get(key) for message in messages if message.get(key)]
        if values:
            merged[key] = "\n".join(values)
    return merged


def _portable_reasoning_items(reasoning_items: list[dict]) -> list[dict]:
    """Return only reasoning items that can be replayed without provider state."""
    return [
        item
        for item in reasoning_items
        if isinstance(item, dict) and item.get("encrypted_content")
    ]


def _remove_unencrypted_reasoning_items(messages: list[dict]) -> int:
    """Remove stale ID-only reasoning items from an existing message history."""
    removed = 0
    for message in messages:
        reasoning_items = message.get("reasoning_items")
        if not reasoning_items:
            continue

        portable_items = _portable_reasoning_items(reasoning_items)
        removed += len(reasoning_items) - len(portable_items)
        if portable_items:
            message["reasoning_items"] = portable_items
        else:
            message.pop("reasoning_items", None)

    return removed


def _is_missing_response_item_error(error: Exception) -> bool:
    """Identify the transient Azure Responses missing-item failure."""
    message = str(error)
    return (
        "Item with id" in message
        and "not found" in message
        and "invalid_request_error" in message
    )


def _parse_skill_metadata(skill_path: Path, content: str) -> dict:
    """Extract lightweight metadata from a SKILL.md frontmatter block."""
    metadata = {
        "name": skill_path.parent.name,
        "description": "",
        "tools": [],
    }

    if not content.startswith("---"):
        return metadata

    try:
        frontmatter = content.split("---", 2)[1]
    except IndexError:
        return metadata

    in_tools = False
    for line in frontmatter.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("name:"):
            metadata["name"] = stripped.split(":", 1)[1].strip().strip('"\'') or metadata["name"]
            in_tools = False
        elif stripped.startswith("description:"):
            metadata["description"] = stripped.split(":", 1)[1].strip().strip('"\'')
            in_tools = False
        elif stripped.startswith("tools:"):
            in_tools = True
        elif in_tools and stripped.startswith("- "):
            metadata["tools"].append(stripped[2:].strip().strip('"\''))
        elif not stripped.startswith("#"):
            in_tools = False

    return metadata


def _load_skills_bank(skills_bank_dir: Path) -> dict[str, dict]:
    """Load all filesystem-backed CAR-assistant skills."""
    if not skills_bank_dir.exists():
        logger.warning("Skills bank directory not found", skills_bank_dir=str(skills_bank_dir))
        return {}

    skills = {}
    for skill_path in sorted(skills_bank_dir.glob("*/SKILL.md")):
        try:
            content = skill_path.read_text(encoding="utf-8")
        except OSError as exc:
            logger.warning("Failed to read skill file", skill_path=str(skill_path), error=str(exc))
            continue

        metadata = _parse_skill_metadata(skill_path, content)
        name = metadata["name"]
        skills[name] = {
            "name": name,
            "description": metadata["description"],
            "tools": metadata["tools"],
            "content": content.strip(),
            "path": str(skill_path),
        }

    return skills


def _format_skill_index(skills: dict[str, dict]) -> str:
    lines = []
    for name in sorted(skills):
        skill = skills[name]
        tools = ", ".join(skill.get("tools") or [])
        suffix = f" Tools: {tools}." if tools else ""
        lines.append(f"- {name}: {skill.get('description', '')}{suffix}")
    return "\n".join(lines)


class CARBenchAgentExecutor(AgentExecutor):
    """Executor for the CAR-bench agent under test using native tool calling."""

    def __init__(
        self,
        model: str,
        temperature: float | None = None,
        thinking: bool = False,
        reasoning_effort: str = "medium",
        interleaved_thinking: bool = False,
        api_mode: str = "chat",
        responses_state_mode: str = "stateless",
    ):
        self.model = model
        self.temperature = temperature
        self.thinking = thinking
        self.reasoning_effort = reasoning_effort  # Can be 'none', 'disable', 'low', 'medium', 'high', or integer token budget
        self.interleaved_thinking = interleaved_thinking  # Whether to use interleaved thinking
        self.api_mode = api_mode
        self.responses_state_mode = responses_state_mode
        print(f"\033[35mModel: {model}, temperature: {temperature} thinking: {thinking}, reasoning_effort: {reasoning_effort}, interleaved thinking: {interleaved_thinking}, api mode: {api_mode}, responses state mode: {responses_state_mode}\033[0m")
        logger.info(
            "Initialized CAR-bench agent",
            model=model,
            thinking=thinking,
            reasoning_effort=reasoning_effort,
            interleaved_thinking=interleaved_thinking,
            api_mode=api_mode,
            responses_state_mode=responses_state_mode,
        )
        self.skill_injection_location = SKILL_INJECTION_LOCATION
        self.ctx_id_to_messages: dict[str, list[dict]] = {}
        self.ctx_id_to_tools: dict[str, list[dict]] = {}
        self.ctx_id_to_last_selected_skill_names: dict[str, list[str]] = {}
        # Per-context turn metrics accumulation (reset when final response is sent)
        self.ctx_id_to_turn_metrics: dict[str, dict] = {}
        self.skills_bank_dir = Path(os.getenv("CAR_BENCH_SKILLS_BANK_DIR", str(DEFAULT_SKILLS_BANK_DIR)))
        self.skills = _load_skills_bank(self.skills_bank_dir)
        self.skill_index = _format_skill_index(self.skills)

    def _record_llm_metrics(
        self,
        context_id: str,
        response,
        elapsed_ms: float,
        num_calls: int = 1,
    ) -> None:
        if context_id not in self.ctx_id_to_turn_metrics:
            self.ctx_id_to_turn_metrics[context_id] = {
                PROMPT_TOKENS: 0,
                COMPLETION_TOKENS: 0,
                THINKING_TOKENS: 0,
                COST: 0.0,
                NUM_LLM_CALLS: 0,
                "_total_llm_time_ms": 0.0,
            }

        turn_m = self.ctx_id_to_turn_metrics[context_id]
        usage = getattr(response, "usage", None)
        if usage:
            turn_m[PROMPT_TOKENS] += getattr(usage, "prompt_tokens", 0) or 0
            turn_m[COMPLETION_TOKENS] += getattr(usage, "completion_tokens", 0) or 0
            # Some providers report thinking/reasoning tokens in completion_tokens_details
            details = getattr(usage, "completion_tokens_details", None)
            if details:
                turn_m[THINKING_TOKENS] += getattr(details, "reasoning_tokens", 0) or 0
        turn_m[COST] += getattr(response, "_hidden_params", {}).get("response_cost", 0.0) or 0.0
        turn_m[NUM_LLM_CALLS] += num_calls
        turn_m["_total_llm_time_ms"] += elapsed_ms

    @staticmethod
    def _content_to_text(content) -> str:
        if content is None:
            return ""
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts = []
            for item in content:
                if isinstance(item, dict):
                    parts.append(str(item.get("text") or item.get("content") or item))
                else:
                    parts.append(str(item))
            return "\n".join(parts)
        return str(content)

    @staticmethod
    def _truncate_text(text: str, max_chars: int = 2500) -> str:
        if len(text) <= max_chars:
            return text
        return text[: max_chars - 20] + "... [truncated]"

    def _compact_message_for_skill_selection(self, message: dict) -> str:
        role = message.get("role", "unknown")
        if role == "assistant" and message.get("tool_calls"):
            calls = []
            for tool_call in message.get("tool_calls") or []:
                function = tool_call.get("function", {})
                calls.append({
                    "name": function.get("name"),
                    "arguments": function.get("arguments"),
                })
            return f"assistant tool calls: {self._truncate_text(json.dumps(calls, ensure_ascii=False), 1800)}"

        content = self._content_to_text(message.get("content"))
        if role == "tool":
            return f"tool result: {self._truncate_text(content, 1800)}"
        if role == "system":
            return f"system: {self._truncate_text(content, 1000)}"
        return f"{role}: {self._truncate_text(content, 1800)}"

    def _build_skill_selection_user_prompt(self, messages: list[dict], tools: list[dict]) -> str:
        recent_messages = messages[-8:]
        conversation = "\n\n".join(
            self._compact_message_for_skill_selection(message)
            for message in recent_messages
        )
        tool_names = []
        for tool in tools or []:
            function = tool.get("function", {}) if isinstance(tool, dict) else {}
            name = function.get("name")
            if name:
                tool_names.append(name)
        available_tools = ", ".join(tool_names) if tool_names else "None provided on this turn"
        return (
            "Select the relevant skill(s) for the assistant's next response.\n\n"
            f"Available runtime tool names: {available_tools}\n\n"
            f"Recent conversation:\n{conversation}"
        )

    def _parse_selected_skill_names(self, content: str) -> list[str]:
        valid_names = set(self.skills)
        candidates = []
        try:
            parsed = json.loads(content)
            if isinstance(parsed, dict):
                candidates = parsed.get("skills", [])
            elif isinstance(parsed, list):
                candidates = parsed
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", content, flags=re.DOTALL)
            if match:
                try:
                    parsed = json.loads(match.group(0))
                    if isinstance(parsed, dict):
                        candidates = parsed.get("skills", [])
                except json.JSONDecodeError:
                    candidates = []
            if not candidates:
                candidates = sorted(
                    (name for name in valid_names if name in content),
                    key=content.find,
                )

        if isinstance(candidates, str):
            candidates = [candidates]
        elif not isinstance(candidates, list):
            candidates = []

        selected = []
        for candidate in candidates:
            name = str(candidate).strip()
            if name in valid_names and name not in selected:
                selected.append(name)
            if len(selected) >= 5:
                break
        return selected

    def _select_relevant_skills(
        self,
        *,
        context_id: str,
        messages: list[dict],
        tools: list[dict],
        ctx_logger,
    ) -> list[str]:
        if not self.skills:
            return []
        if not messages or messages[-1].get("role") != "user":
            return []

        selection_messages = [
            {
                "role": "system",
                "content": SKILL_SELECTION_SYSTEM_TEMPLATE.format(skill_index=self.skill_index),
            },
            {
                "role": "user",
                "content": self._build_skill_selection_user_prompt(messages, tools),
            },
        ]
        try:
            completion_kwargs = {
                "model": self.model,
                "reasoning_effort": "high",
            }
            call_start_time = time.perf_counter()
            for _ in range(10):
                try:
                    response = completion(messages=selection_messages, timeout=300, **completion_kwargs)
                    break
                except Exception as e:
                    ctx_logger.warning("Skill selection completion failed; retrying", error=str(e))
                    time.sleep(10)
            call_elapsed_ms = (time.perf_counter() - call_start_time) * 1000.0
            self._record_llm_metrics(context_id, response, call_elapsed_ms)

            assistant_content = _assistant_content(response)
            content = self._content_to_text(assistant_content.get("content", ""))
            selected = self._parse_selected_skill_names(content)
            ctx_logger.info(
                f"Selected skills from {str(self.skills_bank_dir)[-20:]}, it will be injected into {self.skill_injection_location}; Skill first: 1; Retrieve once: 0",
                selected_skills=selected,
                raw_selection=self._truncate_text(content, 500),
            )
            return selected
        except Exception as exc:
            ctx_logger.warning("Skill selection failed; continuing without skills", error=str(exc))
            return []

    def _format_selected_skill_context(self, selected_skill_names: list[str]) -> str:
        skill_sections = [SKILL_CONTEXT_HEADER]
        for name in selected_skill_names:
            skill = self.skills.get(name)
            if not skill:
                continue
            skill_sections.append(f"\n--- Skill: {name} ---\n{skill['content']}")
        return "\n".join(skill_sections).strip()

    def _selected_skill_paths(self, selected_skill_names: list[str]) -> list[str]:
        return [
            skill["path"]
            for name in selected_skill_names
            if (skill := self.skills.get(name)) and skill.get("path")
        ]

    def _messages_with_selected_skills(
        self,
        messages: list[dict],
        selected_skill_names: list[str],
    ) -> list[dict]:
        llm_messages = copy.deepcopy(messages)
        if not selected_skill_names:
            return llm_messages

        skill_context = self._format_selected_skill_context(selected_skill_names)
        return self._inject_skills_into_system_prompt(llm_messages, skill_context)

    def _inject_skills_into_system_prompt(
        self,
        llm_messages: list[dict],
        skill_context: str,
    ) -> list[dict]:
        if llm_messages and llm_messages[0].get("role") == "system":
            existing_system = self._content_to_text(llm_messages[0].get("content"))
            llm_messages[0]["content"] = f"{skill_context}\n\n\n{existing_system}"
        else:
            llm_messages.insert(
                0,
                {"role": "system", "content": f"{skill_context}\n\n\n{SYSTEM_PROMPT}"},
            )
        return llm_messages

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        inbound_message = context.message
        ctx_logger = logger.bind(role="agent_under_test", context=f"ctx:{context.context_id[:8]}")

        # Initialize or get conversation history
        if context.context_id not in self.ctx_id_to_messages:
            self.ctx_id_to_messages[context.context_id] = []

        messages = self.ctx_id_to_messages[context.context_id]
        tools = self.ctx_id_to_tools.get(context.context_id, [])

        # Parse the incoming A2A Message with Parts (now protobuf)
        user_message_text = None
        incoming_tool_results = None  # Structured tool results from evaluator

        try:
            for part in inbound_message.parts:
                content_type = part.WhichOneof("content")
                if content_type == "text":
                    text = part.text
                    # Parse system prompt and user message from formatted text
                    if "System:" in text and "\n\nUser:" in text:
                        # First message with system prompt
                        parts_split = text.split("\n\nUser:", 1)
                        system_prompt = parts_split[0].replace("System:", "").strip()
                        user_message_text = parts_split[1].strip()
                        if not messages:  # Only add system prompt once
                            messages.append({"role": "system", "content": system_prompt})
                    else:
                        # Regular user message
                        user_message_text = text

                elif content_type == "data":
                    # Extract tools or tool results from data Part
                    data = MessageToDict(part.data)
                    if "tools" in data:
                        tools = data["tools"]
                        self.ctx_id_to_tools[context.context_id] = tools
                    elif "tool_results" in data:
                        # Structured tool results from the evaluator
                        incoming_tool_results = data["tool_results"]

            # Fallback if no text part and no structured tool results found
            if not user_message_text and not incoming_tool_results:
                user_message_text = context.get_user_input()

            ctx_logger.info(
                "Received user message",
                context_id=context.context_id[:8],
                turn=len(messages) + 1,
                message_preview=(user_message_text[:100] if user_message_text else
                                 f"[{len(incoming_tool_results)} tool results]" if incoming_tool_results else "")
            )
            ctx_logger.debug(
                "Message details",
                context_id=context.context_id[:8],
                message=user_message_text,
                num_parts=len(inbound_message.parts),
                has_tools=bool(tools),
                num_tools=len(tools) if tools else 0,
                has_tool_results=bool(incoming_tool_results),
                num_tool_results=len(incoming_tool_results) if incoming_tool_results else 0
            )

        except Exception as e:
            logger.warning(f"Failed to parse message parts: {e}, using fallback")
            user_message_text = context.get_user_input()

        # Check if previous message had tool calls - if so, format as tool results
        if messages and messages[-1].get("role") == "assistant" and messages[-1].get("tool_calls"):
            prev_tool_calls = messages[-1]["tool_calls"]

            if incoming_tool_results:
                # Structured tool results from evaluator — match each result
                # to its corresponding tool_call_id by tool name
                tool_call_by_name = {}
                for tc in prev_tool_calls:
                    name = tc["function"]["name"]
                    # If multiple calls to the same tool, use a list
                    tool_call_by_name.setdefault(name, []).append(tc)

                tool_results = []
                for tr in incoming_tool_results:
                    tr_name = tr.get("tool_name", "") if isinstance(tr, dict) else tr.get("toolName", "")
                    matching_calls = tool_call_by_name.get(tr_name, [])
                    if matching_calls:
                        # Pop the first matching call to handle duplicate tool names
                        matched_tc = matching_calls.pop(0)
                        tool_results.append({
                            "role": "tool",
                            "tool_call_id": matched_tc["id"],
                            "content": tr.get("content", ""),
                        })
                    else:
                        # Fallback: no matching tool_call found, use first unmatched
                        ctx_logger.warning(
                            "No matching tool_call_id for tool result",
                            tool_name=tr_name,
                        )
                        tool_results.append({
                            "role": "tool",
                            "tool_call_id": tr.get("tool_call_id", tr.get("toolCallId", f"unknown_{tr_name}")),
                            "content": tr.get("content", ""),
                        })
            else:
                # Fallback: no structured tool results, use the text message
                # for all tool calls (legacy behavior)
                tool_results = []
                for tc in prev_tool_calls:
                    tool_results.append({
                        "role": "tool",
                        "tool_call_id": tc["id"],
                        "content": user_message_text or "",
                    })

            # Add all tool result messages
            messages.extend(tool_results)

            ctx_logger.debug(
                "Formatted tool results",
                num_tools=len(tool_results),
                tool_call_ids=[tr["tool_call_id"] for tr in tool_results]
            )
        else:
            # Regular user message
            messages.append({"role": "user", "content": user_message_text})

        selected_skill_names = self._select_relevant_skills(  # Skills are only temporarily injected into the system prompt or user content and removed on the next turn
            context_id=context.context_id,
            messages=messages,
            tools=tools,
            ctx_logger=ctx_logger,
        )
        if selected_skill_names:
            self.ctx_id_to_last_selected_skill_names[context.context_id] = selected_skill_names
            selected_skill_source = "retrieved"
        else:
            selected_skill_names = self.ctx_id_to_last_selected_skill_names.get(context.context_id, [])
            selected_skill_source = "cached" if selected_skill_names else "none"
        llm_messages = self._messages_with_selected_skills(
            messages,
            selected_skill_names,
        )

        # Call LLM with native tool calling
        try:
            tools_for_llm = copy.deepcopy(tools) if tools else []

            # Configure prompt caching (guard against empty lists)
            if tools_for_llm:
                tools_for_llm[-1]["function"]["cache_control"] = {"type": "ephemeral"}
            if llm_messages:
                llm_messages[0]["cache_control"] = {"type": "ephemeral"}

            completion_kwargs = _completion_kwargs(
                model=self.model,
                tools=tools_for_llm,
                temperature=self.temperature,
                thinking=self.thinking,
                reasoning_effort=self.reasoning_effort,
                interleaved_thinking=self.interleaved_thinking,
                api_mode=self.api_mode,
                responses_state_mode=self.responses_state_mode,
            )

            call_start_time = time.perf_counter()
            for _ in range(10):
                try:
                    response = completion(
                        messages=llm_messages,
                        timeout=300,
                        **completion_kwargs
                    )
                    break
                except Exception as e:
                    time.sleep(10)

            # Accumulate turn metrics for this LLM call
            call_end_time = time.perf_counter()
            call_elapsed_ms = (call_end_time - call_start_time) * 1000.0
            self._record_llm_metrics(context.context_id, response, call_elapsed_ms)

            # Get the message from LLM
            assistant_content = _assistant_content(response)

            # Extract tool calls from assistant content
            tool_calls = assistant_content.get("tool_calls")

            ctx_logger.info(
                "LLM response received",
                has_tool_calls=bool(tool_calls),
                num_tool_calls=len(tool_calls) if tool_calls else 0,
                has_content=bool(assistant_content.get("content")),
                content_length=len(assistant_content.get("content") or ""),
                has_thinking=bool(assistant_content.get("thinking_blocks") or assistant_content.get("reasoning_content"))
            )
            ctx_logger.debug(
                "LLM response details",
                context_id=context.context_id[:8],
                content=assistant_content.get("content"),
                tool_calls=[{"name": tc["function"]["name"], "args": tc["function"]["arguments"]} for tc in tool_calls] if tool_calls else None,
                reasoning_content=assistant_content.get("reasoning_content")
            )

            # Build proper A2A Message with Parts (protobuf)
            parts = []

            # Add text Part if there's content
            if assistant_content.get("content"):
                parts.append(new_text_part(assistant_content["content"]))

            # Add data Part if there are tool calls
            if assistant_content.get("tool_calls"):
                tool_calls_list = [
                    ToolCall(
                        tool_name=tc["function"]["name"],
                        arguments=json.loads(tc["function"]["arguments"]),
                    )
                    for tc in assistant_content["tool_calls"]
                ]
                tool_calls_data = ToolCallsData(tool_calls=tool_calls_list)
                parts.append(new_data_part(tool_calls_data.model_dump()))

            # Add reasoning_content as data Part for debugging (if present)
            if assistant_content.get("reasoning_content"):
                parts.append(new_data_part({"reasoning_content": assistant_content["reasoning_content"]}))

            # If no parts, add empty text
            if not parts:
                parts.append(new_text_part(assistant_content.get("content", "")))

            ctx_logger.debug(
                "Sending response",
                context_id=context.context_id[:8],
                num_parts=len(parts),
            )

        except Exception as e:
            logger.error(f"LLM error: {e}")
            # Error response as Parts
            parts = [new_text_part(f"Error processing request: {str(e)}")]
            # Create a simple assistant_content for error case
            assistant_content = {"content": f"Error processing request: {str(e)}"}

        # Add to history - preserve complete assistant message including thinking blocks
        # Store the full assistant_content to preserve thinking blocks and reasoning_content
        assistant_message_for_history = {
            "role": "assistant",
            "content": assistant_content.get("content"),
        }

        # Preserve tool calls in proper format for LLM API
        if assistant_content.get("tool_calls"):
            assistant_message_for_history["tool_calls"] = assistant_content["tool_calls"]

        # Preserve thinking blocks and reasoning content for Claude extended thinking
        if assistant_content.get("thinking_blocks"):
            assistant_message_for_history["thinking_blocks"] = assistant_content["thinking_blocks"]
        if assistant_content.get("reasoning_content"):
            assistant_message_for_history["reasoning_content"] = assistant_content["reasoning_content"]
        if assistant_content.get("reasoning_items"):
            reasoning_items = assistant_content["reasoning_items"]
            if (
                self.api_mode == "responses"
                and self.responses_state_mode == "stateless"
            ):
                portable_items = _portable_reasoning_items(reasoning_items)
                dropped_items = len(reasoning_items) - len(portable_items)
                if dropped_items:
                    ctx_logger.warning(
                        "Dropping non-portable Responses reasoning items",
                        dropped_reasoning_items=dropped_items,
                    )
                reasoning_items = portable_items
            if reasoning_items:
                assistant_message_for_history["reasoning_items"] = reasoning_items

        messages.append(assistant_message_for_history)

        # Always return a Message — the agent under test is a conversational participant
        # in a multi-turn exchange. The evaluator decides when the task is done.
        response_message = new_message(
            parts=parts,
            context_id=context.context_id,
            role=Role.ROLE_AGENT,
        )
        response_message.metadata.update({
            SELECTED_SKILLS_METADATA_KEY: selected_skill_names,
            SELECTED_SKILLS_PATH_METADATA_KEY: self._selected_skill_paths(selected_skill_names),
            SELECTED_SKILLS_SOURCE_METADATA_KEY: selected_skill_source,
        })

        # Attach turn_metrics on final response (no tool calls = turn complete)
        has_tool_calls = bool(assistant_content.get("tool_calls"))
        if not has_tool_calls and context.context_id in self.ctx_id_to_turn_metrics:
            turn_m = self.ctx_id_to_turn_metrics.pop(context.context_id)
            num_calls = turn_m[NUM_LLM_CALLS]
            avg_time = (turn_m["_total_llm_time_ms"] / num_calls) if num_calls > 0 else 0.0
            metrics_data = {
                PROMPT_TOKENS: turn_m[PROMPT_TOKENS],
                COMPLETION_TOKENS: turn_m[COMPLETION_TOKENS],
                COST: turn_m[COST],
                MODEL: self.model,
                THINKING_TOKENS: turn_m[THINKING_TOKENS],
                NUM_LLM_CALLS: num_calls,
                AVG_LLM_CALL_TIME_MS: round(avg_time, 1),
                NUM_PASSES: 1,
            }
            response_message.metadata.update({TURN_METRICS_KEY: metrics_data})
            ctx_logger.info(
                "Attached turn_metrics to final response",
                num_llm_calls=num_calls,
                avg_llm_call_time_ms=round(avg_time, 1),
                prompt_tokens=turn_m[PROMPT_TOKENS],
                completion_tokens=turn_m[COMPLETION_TOKENS],
            )

        await event_queue.enqueue_event(response_message)

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        """Cancel the current execution."""
        logger.bind(role="agent_under_test", context=f"ctx:{context.context_id[:8]}").info(
            "Canceling context",
            context_id=context.context_id[:8]
        )
        if context.context_id in self.ctx_id_to_messages:
            del self.ctx_id_to_messages[context.context_id]
        if context.context_id in self.ctx_id_to_tools:
            del self.ctx_id_to_tools[context.context_id]
        if context.context_id in self.ctx_id_to_last_selected_skill_names:
            del self.ctx_id_to_last_selected_skill_names[context.context_id]
        if context.context_id in self.ctx_id_to_turn_metrics:
            del self.ctx_id_to_turn_metrics[context.context_id]
