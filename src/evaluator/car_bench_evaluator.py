"""
CAR-bench evaluator that runs CAR-bench evaluation on an agent under test.

This agent:
1. Sets up CAR-bench voice assistant environments
2. Sends task prompts to the agent under test
(wrapped in a RemoteA2AAgent that communicates via A2A protocol)
3. Parses the agent under test's tool-call responses
4. Steps through the environment and collects metrics
"""
import argparse
import asyncio
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any, List, Dict, Tuple, Optional

import nest_asyncio
import uvicorn
from dotenv import load_dotenv

load_dotenv()

from a2a.server.tasks import TaskUpdater
from a2a.types import TaskState
from a2a.helpers.proto_helpers import (
    new_text_part,
    new_data_part,
    new_text_message,
)
from google.protobuf.json_format import MessageToDict

from agentbeats.evaluator_executor import EvaluatorAgent
from agentbeats.models import EvalRequest
from agentbeats.tool_provider import ToolProvider

sys.path.insert(0, str(Path(__file__).parent.parent))
from logging_utils import configure_logger
from turn_metrics import (
    TURN_METRICS_KEY, SOURCE_KEY, SOURCE_USER, SOURCE_ENVIRONMENT,
    extract_turn_metrics, reported_turn_metric_fields,
    AVG_LLM_CALL_TIME_MS, NUM_LLM_CALLS, COST,
    QUOTA_WAIT_TIME_MS, PROMPT_TOKENS, COMPLETION_TOKENS, THINKING_TOKENS,
)
try:
    from car_bench_paths import CAR_BENCH_REPO
except ModuleNotFoundError:
    from .car_bench_paths import CAR_BENCH_REPO
sys.path.pop(0)

# Import run.py from car-bench repo root
sys.path.insert(0, str(CAR_BENCH_REPO))
from run import run as run_benchmark
sys.path.pop(0)

# Import from car_bench package
from car_bench.types import Action, EnvRunResult

nest_asyncio.apply()
logger = configure_logger(role="evaluator", context="-")

RESPOND_ACTION_NAME = "respond"
EVALUATOR_METRICS_KEY = "evaluator_metrics"
A2A_TURN_TIME_MS = "a2a_turn_time_ms"
A2A_EFFECTIVE_TURN_TIME_MS = "a2a_effective_turn_time_ms"
AGENT_PROMPT_TOKENS = "agent_prompt_tokens"
AGENT_COMPLETION_TOKENS = "agent_completion_tokens"
AGENT_THINKING_TOKENS = "agent_thinking_tokens"
AGENT_INPUT_TOKENS = "agent_input_tokens"
AGENT_OUTPUT_TOKENS = "agent_output_tokens"
AGENT_TOTAL_TOKENS = "agent_total_tokens"


def _schema_has_type(schema: Dict[str, Any], schema_type: str) -> bool:
    declared_type = schema.get("type")
    if isinstance(declared_type, str):
        return declared_type == schema_type
    if isinstance(declared_type, list):
        return schema_type in declared_type
    return False


def _is_integral_float(value: Any) -> bool:
    return (
        isinstance(value, float)
        and not isinstance(value, bool)
        and value.is_integer()
    )


def _tool_parameter_schemas(
    tools_info: List[Dict[str, Any]] | None,
) -> Dict[str, Dict[str, Any]]:
    schemas: Dict[str, Dict[str, Any]] = {}
    for tool in tools_info or []:
        if not isinstance(tool, dict):
            continue
        function = tool.get("function")
        if not isinstance(function, dict):
            continue
        name = function.get("name")
        parameters = function.get("parameters")
        if isinstance(name, str) and isinstance(parameters, dict):
            schemas[name] = parameters
    return schemas


def _normalize_value_for_schema(value: Any, schema: Any) -> Any:
    if not isinstance(schema, dict):
        return value

    if _schema_has_type(schema, "integer") and _is_integral_float(value):
        return int(value)

    is_object_schema = _schema_has_type(schema, "object") or "properties" in schema
    if isinstance(value, dict) and is_object_schema:
        properties = schema.get("properties", {})
        additional_properties = schema.get("additionalProperties")
        normalized = {}
        for key, item in value.items():
            if isinstance(properties, dict) and key in properties:
                normalized[key] = _normalize_value_for_schema(item, properties[key])
            elif isinstance(additional_properties, dict):
                normalized[key] = _normalize_value_for_schema(
                    item,
                    additional_properties,
                )
            else:
                normalized[key] = item
        return normalized

    is_array_schema = _schema_has_type(schema, "array") or "items" in schema
    if isinstance(value, list) and is_array_schema:
        item_schema = schema.get("items")
        return [_normalize_value_for_schema(item, item_schema) for item in value]

    return value


def _normalize_tool_arguments(
    tool_name: str,
    arguments: Any,
    tool_parameter_schemas: Dict[str, Dict[str, Any]] | None,
) -> Any:
    if not isinstance(arguments, dict):
        return arguments
    if not tool_parameter_schemas:
        return arguments
    schema = tool_parameter_schemas.get(tool_name)
    if not isinstance(schema, dict):
        return arguments
    return _normalize_value_for_schema(arguments, schema)


def _parse_tool_calls_data(
    tool_calls_data: list,
    tool_parameter_schemas: Dict[str, Dict[str, Any]] | None = None,
) -> list:
    """Parse A2A tool-call data into the format expected by CAR-bench core."""
    parsed_tool_calls = []
    for tc in tool_calls_data:
        tool_name = tc.get("tool_name", tc.get("toolName", ""))
        arguments = _normalize_tool_arguments(
            tool_name,
            tc.get("arguments", {}),
            tool_parameter_schemas,
        )
        parsed_tool_calls.append({
            "id": f"call_{hash(json.dumps(tc)) % 100000000:08x}",
            "type": "function",
            "function": {
                "name": tool_name,
                "arguments": json.dumps(arguments),
            },
        })
    return parsed_tool_calls


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _sum_quota_wait_seconds(results_by_split: Dict[str, List[EnvRunResult]]) -> float:
    total_ms = 0.0
    for results in results_by_split.values():
        for result in results:
            for message in getattr(result, "traj", []) or []:
                if not isinstance(message, dict):
                    continue
                metrics = message.get("turn_metrics")
                if not isinstance(metrics, dict):
                    continue
                total_ms += _safe_float(metrics.get(QUOTA_WAIT_TIME_MS, 0.0))
    return total_ms / 1000.0


def _sum_successful_llm_time_seconds(
    results_by_split: Dict[str, List[EnvRunResult]],
) -> float:
    total_ms = 0.0
    for results in results_by_split.values():
        for result in results:
            info = getattr(result, "info", {}) or {}
            total_ms += _safe_float(
                info.get("total_llm_induced_latency_ms", 0.0)
            )
    return total_ms / 1000.0


def _a2a_turn_times_ms(trajectory: List[Dict[str, Any]]) -> List[float]:
    times = []
    for message in trajectory:
        if not isinstance(message, dict):
            continue
        metrics = message.get(EVALUATOR_METRICS_KEY)
        if not isinstance(metrics, dict):
            continue
        value = metrics.get(A2A_TURN_TIME_MS)
        if isinstance(value, (int, float)):
            times.append(float(value))
    return times


def _a2a_timing_summary(trajectory: List[Dict[str, Any]]) -> Dict[str, Any]:
    turn_times_ms = _a2a_turn_times_ms(trajectory)
    total_time_ms = sum(turn_times_ms)
    return {
        "a2a_turn_times_ms": [round(value, 1) for value in turn_times_ms],
        "num_a2a_turns": len(turn_times_ms),
        "total_a2a_time_ms": round(total_time_ms, 1),
        "mean_a2a_turn_time_ms": (
            round(total_time_ms / len(turn_times_ms), 1)
            if turn_times_ms
            else 0.0
        ),
    }


def _agent_token_summary(trajectory: List[Dict[str, Any]]) -> Dict[str, int]:
    prompt_tokens = 0
    completion_tokens = 0
    thinking_tokens = 0

    for message in trajectory:
        if not isinstance(message, dict):
            continue
        metrics = message.get("turn_metrics")
        if not isinstance(metrics, dict):
            continue
        prompt_tokens += int(_safe_float(metrics.get(PROMPT_TOKENS, 0)))
        completion_tokens += int(_safe_float(metrics.get(COMPLETION_TOKENS, 0)))
        thinking_tokens += int(_safe_float(metrics.get(THINKING_TOKENS, 0)))

    return {
        AGENT_INPUT_TOKENS: prompt_tokens,
        AGENT_OUTPUT_TOKENS: completion_tokens + thinking_tokens,
        AGENT_PROMPT_TOKENS: prompt_tokens,
        AGENT_COMPLETION_TOKENS: completion_tokens,
        AGENT_THINKING_TOKENS: thinking_tokens,
        AGENT_TOTAL_TOKENS: prompt_tokens + completion_tokens + thinking_tokens,
    }


def _non_system_trajectory(result: EnvRunResult) -> List[Dict[str, Any]]:
    return [
        msg for msg in result.traj
        if isinstance(msg, dict) and msg.get("role") != "system"
    ]


def _detailed_result_row(result: EnvRunResult) -> Dict[str, Any]:
    trajectory = _non_system_trajectory(result)
    return {
        "task_id": result.task_id,
        "reward": result.reward,
        "trial": result.trial,
        "reward_info": result.info.get("reward_info", {}),
        "task": result.info.get("task", {}),
        "trajectory": trajectory,
        "error": result.info.get("error", None),
        "traceback": result.info.get("traceback", None),
        "user_cost": result.info.get("user_cost", 0),
        "total_agent_cost": result.info.get("total_agent_cost", 0),
        "total_llm_latency_ms": result.info.get("total_llm_induced_latency_ms", 0),
        **_a2a_timing_summary(trajectory),
        **_agent_token_summary(trajectory),
    }


def create_remote_agent_factory(agent_url: str):
    """Create a factory that produces RemoteA2AAgent instances.

    Each agent gets its own ToolProvider to avoid threading issues.
    """
    def factory(tools_info, wiki, args):
        # Import Agent base class and types
        from car_bench.agents.base import Agent
        from car_bench.types import AgentState

        # Create an agent that delegates to the remote agent under test via A2A.
        class RemoteA2AAgent(Agent):
            def __init__(self, agent_url: str):
                self.agent_url = agent_url
                self.tool_provider = ToolProvider()
                self._is_first_message = True

            def get_init_state(self, system_prompt: str, initial_observation: str) -> AgentState:
                """Initialize agent state with system prompt and initial observation."""
                self._is_first_message = True
                return AgentState(
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": initial_observation},
                    ]
                )

            def generate_next_message(self, state: AgentState, tools_info: List[Dict[str, Any]]) -> Tuple[Dict[str, Any], AgentState]:
                """Generate next message by calling remote agent under test."""
                import asyncio

                # Collect trailing tool result messages (there may be multiple from parallel tool calls)
                tool_result_messages = []
                for msg in reversed(state.messages):
                    if msg.get("role") == "tool":
                        tool_result_messages.insert(0, msg)
                    else:
                        break

                # Extract last user/tool message content
                last_user_msg = state.messages[-1]["content"]

                # Handle empty messages - replace with placeholder to avoid LLM errors
                if not last_user_msg or not last_user_msg.strip():
                    logger.warning(
                        "Empty user message detected, using placeholder 'none'",
                        message_index=len(state.messages) - 1
                    )
                    last_user_msg = "none"

                # Build proper A2A message with Parts (protobuf)
                if self._is_first_message:
                    # First message: combine system prompt and user message in one text Part,
                    # send tools as separate data Part
                    parts = []

                    # Combine system prompt and user message into single text Part
                    system_prompt = state.messages[0]["content"] if state.messages[0]["role"] == "system" else ""
                    prompt_text = f"System: {system_prompt}\n\nUser: {last_user_msg}" if system_prompt else last_user_msg
                    parts.append(new_text_part(prompt_text))

                    # Add tools as data Part (structured data)
                    if tools_info:
                        parts.append(new_data_part({"tools": tools_info}))

                    source_tag = SOURCE_USER
                elif len(tool_result_messages) > 0:
                    # Tool result turn: send individual results as structured data Part
                    # so the agent under test can match each result to its tool_call_id
                    tool_results_data = [
                        {
                            "tool_name": msg.get("name", ""),
                            "tool_call_id": msg.get("tool_call_id", ""),
                            "content": msg.get("content", ""),
                        }
                        for msg in tool_result_messages
                    ]
                    parts = [new_data_part({"tool_results": tool_results_data})]
                    source_tag = SOURCE_ENVIRONMENT
                else:
                    # Regular user message
                    parts = [new_text_part(last_user_msg)]
                    source_tag = SOURCE_USER

                outbound_metadata = {SOURCE_KEY: source_tag}

                # Call remote agent via A2A
                # Use synchronous call since we're in a thread pool executor
                is_new_conversation = self._is_first_message
                self._is_first_message = False

                # Build content preview for outbound log
                if source_tag == SOURCE_USER:
                    outbound_preview = last_user_msg[:120] if last_user_msg else ""
                else:
                    # Environment: show raw tool results as compact JSON
                    tool_summaries = []
                    for msg in tool_result_messages:
                        name = msg.get("name", "?")
                        tool_summaries.append({"tool": name, "result": msg.get("content", "")})
                    outbound_preview = json.dumps(tool_summaries, separators=(",", ":"))

                msg_logger = logger.bind(role=source_tag, context="-")
                msg_logger.debug(
                    "Sending to agent",
                    content_preview=outbound_preview,
                    new_conversation=is_new_conversation,
                )

                # Use synchronous method to avoid event loop issues in thread pool
                turn_start = time.perf_counter()
                response = self.tool_provider.talk_to_agent_with_parts_sync(
                    parts=parts,
                    url=self.agent_url,
                    new_conversation=is_new_conversation,
                    metadata=outbound_metadata,
                )
                turn_time_ms = (time.perf_counter() - turn_start) * 1000.0

                msg_logger.debug(
                    "Received response",
                    turn_time_ms=round(turn_time_ms, 1),
                )

                # Parse response into standard message format
                tool_parameter_schemas = _tool_parameter_schemas(tools_info)
                next_message = self._parse_response(response, tool_parameter_schemas)

                # Extract turn_metrics from response metadata (only on final responses)
                response_metadata = getattr(response, "metadata", None)
                reported_metric_fields = reported_turn_metric_fields(response_metadata)
                turn_metrics = extract_turn_metrics(response_metadata)

                quota_wait_time_ms = _safe_float(
                    turn_metrics.get(QUOTA_WAIT_TIME_MS, 0.0)
                )
                effective_turn_time_ms = max(0.0, turn_time_ms - quota_wait_time_ms)

                # Add evaluator-measured turn time after removing model-quota sleep.
                turn_metrics[QUOTA_WAIT_TIME_MS] = round(quota_wait_time_ms, 1)
                turn_metrics["raw_turn_time_ms"] = round(turn_time_ms, 1)
                turn_metrics["turn_time_ms"] = round(effective_turn_time_ms, 1)

                next_message[EVALUATOR_METRICS_KEY] = {
                    A2A_TURN_TIME_MS: round(turn_time_ms, 1),
                    A2A_EFFECTIVE_TURN_TIME_MS: round(effective_turn_time_ms, 1),
                    QUOTA_WAIT_TIME_MS: round(quota_wait_time_ms, 1),
                }

                # Attach metrics to the message if this is a final response (no tool calls)
                if not next_message.get("tool_calls") and turn_metrics.get(NUM_LLM_CALLS, 0) > 0:
                    if os.environ.get("CAR_BENCH_RUN_DIR"):
                        turn_metrics["_reported_fields"] = reported_metric_fields
                    next_message["turn_metrics"] = turn_metrics

                # Update AgentState cost/latency totals
                additional_cost = turn_metrics.get(COST, 0.0)
                additional_llm_latency = (
                    turn_metrics.get(AVG_LLM_CALL_TIME_MS, 0.0) * turn_metrics.get(NUM_LLM_CALLS, 0)
                )

                # Update state
                updated_state = AgentState(
                    messages=state.messages + [next_message],
                    total_cost=state.total_cost + additional_cost,
                    total_llm_induced_latency_ms=state.total_llm_induced_latency_ms + additional_llm_latency,
                    turn_counter=state.turn_counter,
                    least_prompt_tokens=state.least_prompt_tokens,
                    latest_prompt_tokens=turn_metrics.get("prompt_tokens", state.latest_prompt_tokens),
                )

                return next_message, updated_state

            def _parse_response(
                self,
                response,
                tool_parameter_schemas: Dict[str, Dict[str, Any]] | None = None,
            ) -> Dict[str, Any]:
                """Parse the A2A Message response into standard agent message format.

                Handles both protobuf Message (v1.0) and Pydantic Message (v0.3 compat) formats.
                """
                try:
                    content = None
                    tool_calls = None
                    reasoning_content = None

                    # Get parts from response
                    if hasattr(response, 'parts'):
                        parts = response.parts
                    else:
                        # Fallback: try parsing as JSON string
                        parsed = json.loads(response)
                        parts = parsed.get("parts", [])

                    # Process each part
                    for part in parts:
                        # Handle protobuf Part (v1.0) — has WhichOneof
                        if hasattr(part, 'WhichOneof'):
                            content_type = part.WhichOneof("content")
                            if content_type == "text":
                                content = part.text
                            elif content_type == "data":
                                data = MessageToDict(part.data)
                                if "tool_calls" in data:
                                    tool_calls = self._parse_tool_calls(
                                        data["tool_calls"],
                                        tool_parameter_schemas,
                                    )
                                elif "reasoning_content" in data:
                                    reasoning_content = data["reasoning_content"]
                        # Handle Pydantic Part (v0.3 compat) — has .root attribute
                        elif hasattr(part, 'root'):
                            if hasattr(part.root, 'text') and part.root.text is not None:
                                content = part.root.text
                            elif hasattr(part.root, 'data') and part.root.data is not None:
                                data = part.root.data
                                if "tool_calls" in data:
                                    tool_calls = self._parse_tool_calls(
                                        data["tool_calls"],
                                        tool_parameter_schemas,
                                    )
                                elif "reasoning_content" in data:
                                    reasoning_content = data["reasoning_content"]
                        # Handle dict representation
                        elif isinstance(part, dict):
                            part_data = part.get("root", part)
                            if "text" in part_data and part_data["text"]:
                                content = part_data["text"]
                            elif "data" in part_data and part_data["data"]:
                                data = part_data["data"]
                                if "tool_calls" in data:
                                    tool_calls = self._parse_tool_calls(
                                        data["tool_calls"],
                                        tool_parameter_schemas,
                                    )
                                elif "reasoning_content" in data:
                                    reasoning_content = data["reasoning_content"]

                    parsed_msg = {
                        "role": "assistant",
                        "content": content,
                        "tool_calls": tool_calls,
                    }

                    # Include reasoning_content for debugging if present
                    if reasoning_content:
                        parsed_msg["reasoning_content"] = reasoning_content

                    logger.debug(
                        "Parsed agent response",
                        has_tool_calls=bool(tool_calls),
                        num_tool_calls=len(tool_calls) if tool_calls else 0,
                    )

                    return parsed_msg

                except (json.JSONDecodeError, KeyError) as e:
                    logger.warning(f"Failed to parse agent response: {e}")
                    # If parsing fails, treat as plain text response
                    return {
                        "role": "assistant",
                        "content": response,
                        "tool_calls": None,
                    }

            @staticmethod
            def _parse_tool_calls(
                tool_calls_data: list,
                tool_parameter_schemas: Dict[str, Dict[str, Any]] | None = None,
            ) -> list:
                """Parse tool calls from structured data into LLM format."""
                return _parse_tool_calls_data(
                    tool_calls_data,
                    tool_parameter_schemas,
                )

        return RemoteA2AAgent(agent_url=agent_url)

    return factory


def calculate_evaluation_results(
    results_by_split: Dict[str, List[EnvRunResult]],
    time_used: float,
    *,
    raw_time_used: float | None = None,
    quota_wait_time: float = 0.0,
) -> Tuple[Dict[str, Any], str]:
    """Calculate comprehensive evaluation results and format summary.

    Args:
        results_by_split: Results organized by task split (base, hallucination, disambiguation)
        time_used: Total evaluation time in seconds

    Returns:
        Tuple of (result_data dict, summary string)
    """
    # Import analysis functions from car-bench repo root
    sys.path.insert(0, str(CAR_BENCH_REPO))
    try:
        from analyze_results_v2 import (
            organize_data_by_task_and_trial,
            calculate_pass_power_k_scores,
            calculate_pass_at_k_scores,
        )
    finally:
        sys.path.pop(0)

    # Flatten all results
    all_results = [r for results in results_by_split.values() for r in results]
    total_reward = sum(r.reward for r in all_results)
    num_completed = len(all_results)
    pass_rate = (total_reward / num_completed * 100) if num_completed > 0 else 0
    successful_llm_time_used = _sum_successful_llm_time_seconds(results_by_split)

    # Split task rewards by task type
    task_rewards_by_split = {
        split: {str(r.task_id): r.reward for r in results}
        for split, results in results_by_split.items()
        if results
    }

    # Calculate metrics for each split separately
    pass_power_k_scores_by_split = {}
    pass_at_k_scores_by_split = {}
    max_trials = 1

    for split, results in results_by_split.items():
        if not results:
            continue

        # Convert results to format expected by analyze_results.py
        analysis_data = [
            {
                "task_id": result.task_id,
                "reward": result.reward,
                "info": result.info,
                "trial": result.trial,
            }
            for result in results
        ]

        # Organize data and calculate metrics for this split
        organized_data = organize_data_by_task_and_trial(analysis_data)
        split_max_trials = (
            max(len(trials) for trials in organized_data.values())
            if organized_data else 1
        )
        max_trials = max(max_trials, split_max_trials)

        pass_power_k_scores_by_split[split] = calculate_pass_power_k_scores(organized_data, split_max_trials)
        pass_at_k_scores_by_split[split] = calculate_pass_at_k_scores(organized_data, split_max_trials)

    # Calculate overall metrics as average across splits
    pass_power_k_scores, pass_at_k_scores = calculate_average_metrics_across_splits(
        pass_power_k_scores_by_split,
        pass_at_k_scores_by_split,
        max_trials
    )

    # Prepare detailed results with reward_info, task info, and trajectories - split by task type
    detailed_results_by_split = {}

    for split, results in results_by_split.items():
        if not results:
            continue

        detailed_results_by_split[split] = [
            _detailed_result_row(result)
            for result in results
        ]

    # Format task results for display by split
    task_results_by_split_str = []
    for split in ["base", "hallucination", "disambiguation"]:
        if split in results_by_split and results_by_split[split]:
            results = results_by_split[split]
            split_results = "\n".join(
                f"    Task {r.task_id}: {'✓' if r.reward >= 0.99 else '✗'} ({r.reward:.2f})"
                for r in results
            )
            split_reward = sum(r.reward for r in results)
            split_count = len(results)
            split_pass_rate = (split_reward / split_count * 100) if split_count > 0 else 0
            task_results_by_split_str.append(
                f"  {split.capitalize()}: {split_pass_rate:.1f}% ({split_reward:.1f}/{split_count})\n{split_results}"
            )

    task_results_str = "\n\n".join(task_results_by_split_str)

    # Format Pass^k and Pass@k scores
    pass_scores_str = [
        f"  Pass^{k}: {pass_power_k_scores.get(f'Pass^{k}', 0) * 100:.1f}%  |  Pass@{k}: {pass_at_k_scores.get(f'Pass@{k}', 0) * 100:.1f}%"
        for k in range(1, max_trials + 1)
    ]
    pass_scores_display = "\n".join(pass_scores_str)

    # Build result data
    result_data = {
        "score": total_reward,
        "max_score": num_completed,
        "pass_rate": pass_rate,
        "task_rewards_by_split": task_rewards_by_split,
        "time_used": time_used,
        "raw_time_used": raw_time_used if raw_time_used is not None else time_used,
        "quota_wait_time": quota_wait_time,
        "successful_llm_time_used": successful_llm_time_used,
        "pass_power_k_scores": pass_power_k_scores,
        "pass_at_k_scores": pass_at_k_scores,
        "pass_power_k_scores_by_split": pass_power_k_scores_by_split,
        "pass_at_k_scores_by_split": pass_at_k_scores_by_split,
        "max_trials": max_trials,
        "detailed_results_by_split": detailed_results_by_split,
    }

    # Build summary string
    summary = f"""CAR-bench Results
Tasks: {num_completed}
Overall Pass Rate: {pass_rate:.1f}% ({total_reward:.1f}/{num_completed})
Time: {time_used:.1f}s
Successful LLM Time: {successful_llm_time_used:.1f}s

Pass Scores:
{pass_scores_display}

Task Results by Split:
{task_results_str}"""

    return result_data, summary


def calculate_average_metrics_across_splits(
    pass_power_k_scores_by_split: Dict[str, Dict[str, float]],
    pass_at_k_scores_by_split: Dict[str, Dict[str, float]],
    max_trials: int
) -> Tuple[Dict[str, float], Dict[str, float]]:
    """Calculate average metrics across splits (not weighted by task count).

    Returns:
        Tuple of (pass_power_k_scores, pass_at_k_scores)
    """
    num_splits = len(pass_power_k_scores_by_split)
    if num_splits == 0:
        return {}, {}

    # Average Pass^k and Pass@k scores across splits
    pass_power_k_scores = {}
    pass_at_k_scores = {}

    for k in range(1, max_trials + 1):
        pass_power_key = f"Pass^{k}"
        pass_at_key = f"Pass@{k}"

        # Sum scores across splits
        pass_power_sum = sum(
            scores.get(pass_power_key, 0.0)
            for scores in pass_power_k_scores_by_split.values()
            if pass_power_key in scores
        )
        pass_at_sum = sum(
            scores.get(pass_at_key, 0.0)
            for scores in pass_at_k_scores_by_split.values()
            if pass_at_key in scores
        )

        pass_power_k_scores[pass_power_key] = pass_power_sum / num_splits
        pass_at_k_scores[pass_at_key] = pass_at_sum / num_splits

    return pass_power_k_scores, pass_at_k_scores


def build_args_from_config(config: dict, task_type: str) -> argparse.Namespace:
    """Convert evaluation config to run() arguments for a specific task type."""
    return argparse.Namespace(
        env="car_voice_assistant",
        task_type=task_type,
        task_split=config.get("task_split", "test"),
        num_tasks=config.get(f"tasks_{task_type}_num_tasks", -1),
        task_id_filter=config.get(f"tasks_{task_type}_task_id_filter", None),
        num_trials=config.get("num_trials", 1),
        max_steps=config.get("max_steps", 40),
        max_concurrency=1,  # Sequential to avoid overloading agent under test
        # User simulator settings
        user_strategy="llm",
        user_model=config.get("user_model", "gemini/gemini-2.5-flash"),
        user_model_provider=config.get("user_provider", "gemini"),
        user_thinking=config.get("user_thinking", True),
        # Policy evaluator settings
        policy_evaluator_strategy="llm",
        policy_evaluator_model=config.get("policy_evaluator_model", "gemini/gemini-2.5-flash"),
        policy_evaluator_model_provider=config.get("policy_evaluator_provider", "gemini"),
        evaluate_policy=True,
        score_tool_execution_errors=True,
        score_policy_errors=True,
        # Agent settings (NOT USED for custom agent factory, but required by some code paths)
        agent_strategy="tool-calling",  # Default strategy if factory not used
        model="remote-agent",  # Placeholder, not used for remote agents
        model_provider="a2a", # not used
        temperature=0.0, # not used
        thinking=False, # not used
        interleaved_thinking=False, # not used
        reasoning_effort="none", # not used
        # =======
        use_user_as_a_tool_tools=False,
        planning_and_thinking_tool=True,
        remove_non_standard_fields_from_tools=False,
        few_shot_displays_path=None,
        seed=10,
        shuffle=False,
    )


class CARBenchEvaluator(EvaluatorAgent):
    """Evaluator that runs CAR-bench against one agent under test."""

    def __init__(self):
        self._required_config_keys = []
        self._tool_provider = ToolProvider()

    def validate_request(self, request: EvalRequest) -> tuple[bool, str]:
        missing_config_keys = set(self._required_config_keys) - set(request.config.keys())
        if missing_config_keys:
            return False, f"Missing config keys: {missing_config_keys}"
        return True, "ok"

    async def run_eval(self, req: EvalRequest, updater: TaskUpdater) -> None:
        eval_logger = logger.bind(role="evaluator", context="eval")
        eval_logger.info(
            "Starting CAR-bench evaluation",
            agent_url=str(req.agent_under_test),
            num_trials=req.config.get("num_trials", 1)
        )
        start_time = time.time()

        agent_url = str(req.agent_under_test)

        # Create agent factory
        agent_factory = create_remote_agent_factory(agent_url)

        await updater.update_status(
            TaskState.TASK_STATE_WORKING,
            new_text_message("Starting evaluation of CAR-bench tasks")
        )

        all_results: List[EnvRunResult] = []
        results_by_split: Dict[str, List[EnvRunResult]] = {
            "base": [],
            "hallucination": [],
            "disambiguation": []
        }

        try:
            # Run each task type (base, hallucination, disambiguation)
            for task_type in ["base", "hallucination", "disambiguation"]:
                num_tasks_key = f"tasks_{task_type}_num_tasks"
                task_id_filter_key = f"tasks_{task_type}_task_id_filter"

                # Skip if not configured
                if num_tasks_key not in req.config and task_id_filter_key not in req.config:
                    eval_logger.info(
                        "Skipping task type (not configured)",
                        task_type=task_type
                    )
                    continue

                split_logger = logger.bind(role="evaluator", context=f"type:{task_type}")

                # Build args for this task type
                args = build_args_from_config(req.config, task_type)

                # Log task configuration
                task_desc = f"{task_type} tasks (split={args.task_split}"
                if args.task_id_filter:
                    task_desc += f", ids={args.task_id_filter}"
                elif args.num_tasks > 0:
                    task_desc += f", first {args.num_tasks} tasks"
                else:
                    task_desc += ", all tasks"
                task_desc += ")"

                split_logger.info(
                    "Starting task type evaluation",
                    task_type=task_type,
                    task_split=args.task_split,
                    num_tasks=args.num_tasks,
                    task_id_filter=args.task_id_filter,
                    num_trials=req.config.get("num_trials", 1)
                )

                await updater.update_status(
                    TaskState.TASK_STATE_WORKING,
                    new_text_message(f"Starting evaluation: {task_desc}")
                )

                # Build checkpoint path
                ckpt_path = f"/tmp/car_bench_eval_{task_type}_{args.task_split}.json"

                # Clean up any existing checkpoint file to avoid JSON parse errors
                if os.path.exists(ckpt_path):
                    os.remove(ckpt_path)
                    eval_logger.debug("Removed existing checkpoint file", path=ckpt_path)

                # Run in executor to avoid blocking async event loop
                loop = asyncio.get_event_loop()
                results = await loop.run_in_executor(
                    None,
                    run_benchmark,
                    args,
                    ckpt_path,
                    agent_factory
                )

                all_results.extend(results)
                results_by_split[task_type].extend(results)

                # Log completion with summary stats
                split_reward = sum(r.reward for r in results)
                split_logger.info(
                    "Completed task type",
                    task_type=task_type,
                    num_tasks=len(results),
                    total_reward=split_reward,
                    pass_rate=f"{(split_reward / len(results) * 100) if results else 0:.1f}%"
                )

                # Emit intermediate artifact with per-split results so far
                # This allows crash recovery and live progress tracking
                intermediate_raw_time = time.time() - start_time
                intermediate_quota_wait = _sum_quota_wait_seconds(results_by_split)
                intermediate_time = max(
                    0.0,
                    intermediate_raw_time - intermediate_quota_wait,
                )
                intermediate_data, intermediate_summary = calculate_evaluation_results(
                    {k: v for k, v in results_by_split.items() if v},
                    intermediate_time,
                    raw_time_used=intermediate_raw_time,
                    quota_wait_time=intermediate_quota_wait,
                )
                await updater.add_artifact(
                    parts=[
                        new_text_part(f"[Intermediate] {intermediate_summary}"),
                        new_data_part(intermediate_data),
                    ],
                    name=f"intermediate_{task_type}",
                )

            # Calculate metrics and format results
            raw_time_used = time.time() - start_time
            quota_wait_time = _sum_quota_wait_seconds(results_by_split)
            time_used = max(0.0, raw_time_used - quota_wait_time)
            result_data, summary = calculate_evaluation_results(
                results_by_split,
                time_used,
                raw_time_used=raw_time_used,
                quota_wait_time=quota_wait_time,
            )

            await updater.add_artifact(
                parts=[
                    new_text_part(summary),
                    new_data_part(result_data),
                ],
                name="Result",
            )

        except Exception as e:
            logger.error(f"Evaluation failed: {e}", exc_info=True)
            await updater.update_status(
                TaskState.TASK_STATE_FAILED,
                new_text_message(f"Evaluation failed: {e}")
            )
            raise
