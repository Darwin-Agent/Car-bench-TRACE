import argparse
import os
import sys
import json
import asyncio
import re
import shlex
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
import tomllib

from a2a.client import (
    A2ACardResolver,
    ClientConfig,
    ClientFactory,
)
from a2a.types import (
    SendMessageRequest,
    TaskState,
)
from google.protobuf.json_format import MessageToDict

from agentbeats.client import DEFAULT_TIMEOUT, create_message
from agentbeats.models import EvalRequest


class AgentFailedError(Exception):
    """Raised when an agent returns a non-successful terminal status."""
    pass


def parse_toml(d: dict[str, object]) -> tuple[EvalRequest, str]:
    if "green_agent" in d or "participants" in d:
        raise ValueError("Old scenario shape is unsupported; use [evaluator] and [agent_under_test].")

    evaluator = d.get("evaluator")
    if not isinstance(evaluator, dict) or "endpoint" not in evaluator:
        raise ValueError("evaluator.endpoint is required in TOML")
    evaluator_endpoint: str = evaluator["endpoint"]

    agent_under_test = d.get("agent_under_test")
    if not isinstance(agent_under_test, dict) or "endpoint" not in agent_under_test:
        raise ValueError("agent_under_test.endpoint is required in TOML")

    eval_req = EvalRequest(
        agent_under_test=agent_under_test["endpoint"],
        config=d.get("config", {}) or {},
    )
    return eval_req, evaluator_endpoint


def parse_parts(parts) -> tuple[list, list]:
    """Parse protobuf Parts into text and data lists."""
    text_parts = []
    data_parts = []

    for part in parts:
        content_type = part.WhichOneof("content")
        if content_type == "text":
            try:
                data_item = json.loads(part.text)
                data_parts.append(data_item)
            except Exception:
                text_parts.append(part.text.strip())
        elif content_type == "data":
            data_parts.append(MessageToDict(part.data))

    return text_parts, data_parts


def print_parts(parts, task_state: str | None = None):
    text_parts, data_parts = parse_parts(parts)

    output = []
    if task_state:
        output.append(f"[Status: {task_state}]")
    if text_parts:
        output.append("\n".join(text_parts))
    if data_parts:
        output.extend(json.dumps(item, indent=2) for item in data_parts)

    print("\n".join(output) + "\n")


def _parse_artifact(artifact) -> dict[str, Any]:
    text_parts, data_parts = parse_parts(artifact.parts)
    return {
        "name": getattr(artifact, "name", None),
        "text_parts": text_parts,
        "data_parts": data_parts,
    }


def _is_final_result_data(data: dict[str, Any]) -> bool:
    return all(key in data for key in ("score", "max_score", "pass_rate"))


def _find_final_result(artifact_records: list[dict[str, Any]]) -> tuple[dict[str, Any] | None, str]:
    final_data = None
    final_text = ""

    for artifact in artifact_records:
        is_named_final = artifact.get("name") == "Result"
        for data in artifact.get("data_parts", []):
            if isinstance(data, dict) and _is_final_result_data(data):
                if is_named_final or final_data is None:
                    final_data = data
        for text in artifact.get("text_parts", []):
            if is_named_final or not text.startswith("[Intermediate]"):
                final_text = text

    return final_data, final_text


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _quota_wait_seconds_from_result_data(data: dict[str, Any] | None) -> float:
    if not isinstance(data, dict):
        return 0.0
    if "quota_wait_time" in data:
        return _safe_float(data.get("quota_wait_time"))

    total_ms = 0.0
    detailed = data.get("detailed_results_by_split")
    if not isinstance(detailed, dict):
        return 0.0
    for results in detailed.values():
        if not isinstance(results, list):
            continue
        for result in results:
            if not isinstance(result, dict):
                continue
            for message in result.get("trajectory", []) or []:
                if not isinstance(message, dict):
                    continue
                metrics = message.get("turn_metrics")
                if isinstance(metrics, dict):
                    total_ms += _safe_float(metrics.get("quota_wait_time_ms"))
    return total_ms / 1000.0


def _quota_wait_seconds_from_artifacts(
    final_result: dict[str, Any] | None,
    artifact_records: list[dict[str, Any]],
) -> float:
    quota_wait = _quota_wait_seconds_from_result_data(final_result)
    if quota_wait:
        return quota_wait
    for artifact in reversed(artifact_records):
        for data in artifact.get("data_parts", []):
            quota_wait = _quota_wait_seconds_from_result_data(data)
            if quota_wait:
                return quota_wait
    return 0.0


def print_final_summary(final_data: dict[str, Any] | None, final_text: str) -> None:
    if final_text:
        print(final_text.strip())
        return

    if not final_data:
        print("Evaluation completed, but no final summary artifact was returned.")
        return

    score = final_data.get("score", 0)
    max_score = final_data.get("max_score", 0)
    pass_rate = final_data.get("pass_rate", 0)
    time_used = final_data.get("time_used", 0)
    print(
        "CAR-bench Results\n"
        f"Overall Pass Rate: {pass_rate:.1f}% ({score:.1f}/{max_score})\n"
        f"Time: {time_used:.1f}s"
    )


def _slug(value: object, *, default: str = "unknown", max_len: int = 80) -> str:
    text = str(value or default)
    text = _expand_shell_default(text)
    text = re.sub(r"[^A-Za-z0-9._-]+", "-", text).strip("-._")
    if not text:
        text = default
    return text[:max_len].strip("-._") or default


def _expand_shell_default(value: str) -> str:
    def replace(match: re.Match[str]) -> str:
        fallback = match.group(1)
        return fallback if fallback is not None else match.group(0)

    return re.sub(r"\$\{[A-Za-z_][A-Za-z0-9_]*:-([^}]+)\}", replace, value)


def _command_arg_value(args: list[str], *names: str) -> str | None:
    for index, item in enumerate(args):
        for name in names:
            if item == name and index + 1 < len(args):
                return args[index + 1]
            if item.startswith(f"{name}="):
                return item.split("=", 1)[1]
    return None


def _scenario_name(scenario_path: Path, data: dict[str, Any]) -> str:
    run = data.get("run", {})
    if isinstance(run, dict) and run.get("scenario_name"):
        return str(run["scenario_name"])
    if scenario_path.name == "scenario.toml":
        return scenario_path.parent.name
    return f"{scenario_path.parent.name}/{scenario_path.stem}"


def _agent_name(scenario_path: Path, data: dict[str, Any]) -> str:
    run = data.get("run", {})
    if isinstance(run, dict) and run.get("agent_name"):
        return str(run["agent_name"])
    agent = data.get("agent_under_test", {})
    if isinstance(agent, dict):
        for key in ("name", "result_label"):
            if agent.get(key):
                return str(agent[key])
    return scenario_path.parent.name or "agent_under_test"


def _agent_metadata(data: dict[str, Any]) -> dict[str, Any]:
    run = data.get("run", {})
    metadata: dict[str, Any] = {}
    if isinstance(run, dict) and isinstance(run.get("agent_metadata"), dict):
        metadata.update(run["agent_metadata"])

    agent = data.get("agent_under_test", {})
    if isinstance(agent, dict):
        for key in ("name", "result_label", "result_model", "result_reasoning_effort"):
            if key in agent:
                metadata[key] = agent[key]
        for key, value in agent.get("env", {}).items():
            upper = key.upper()
            if upper in {
                "AGENT_LLM",
                "AGENT_REASONING_EFFORT",
                "CODEX_MODEL",
                "CODEX_REASONING_EFFORT",
                "CODEX_PLANNER_MODEL",
                "CODEX_EXECUTOR_MODEL",
                "CODEX_PLANNER_REASONING_EFFORT",
                "CODEX_EXECUTOR_REASONING_EFFORT",
            }:
                metadata[key] = value
        if "command_args" in agent:
            metadata["command_args"] = agent["command_args"]
        if "cmd" in agent:
            metadata["cmd"] = agent["cmd"]

    return metadata


def _metadata_command_args(metadata: dict[str, Any]) -> list[str]:
    command_args = metadata.get("command_args", [])
    if isinstance(command_args, str):
        command_args = shlex.split(command_args)
    elif not isinstance(command_args, list):
        command_args = []

    cmd = metadata.get("cmd")
    if isinstance(cmd, str) and cmd:
        command_args = [*shlex.split(cmd), *command_args]
    return [str(arg) for arg in command_args]


def _normalize_label(value: object | None) -> str | None:
    if value is None:
        return None
    text = _expand_shell_default(str(value)).strip()
    if not text or text.startswith("${"):
        return None
    return text


def _model_label(metadata: dict[str, Any]) -> str | None:
    if metadata.get("result_model"):
        return _normalize_label(metadata["result_model"])

    planner = _normalize_label(metadata.get("CODEX_PLANNER_MODEL"))
    executor = _normalize_label(metadata.get("CODEX_EXECUTOR_MODEL"))
    if planner and executor:
        return f"{planner}_to_{executor}"

    for key in ("CODEX_EXECUTOR_MODEL", "CODEX_MODEL", "AGENT_LLM"):
        value = _normalize_label(metadata.get(key))
        if value:
            return value

    args = _metadata_command_args(metadata)
    for names in (
        ("--executor-model",),
        ("--model",),
        ("--agent-llm",),
        ("--planner-model",),
    ):
        value = _command_arg_value(args, *names)
        if value:
            return value
    return None


def _reasoning_label(metadata: dict[str, Any]) -> str | None:
    if metadata.get("result_reasoning_effort"):
        return _normalize_label(metadata["result_reasoning_effort"])

    planner = _normalize_label(metadata.get("CODEX_PLANNER_REASONING_EFFORT"))
    executor = _normalize_label(metadata.get("CODEX_EXECUTOR_REASONING_EFFORT"))
    if planner and executor and planner != executor:
        return f"{planner}_to_{executor}"
    if executor:
        return executor

    for key in (
        "CODEX_REASONING_EFFORT",
        "AGENT_REASONING_EFFORT",
    ):
        value = _normalize_label(metadata.get(key))
        if value:
            return value

    args = _metadata_command_args(metadata)
    planner_arg = _command_arg_value(args, "--planner-reasoning-effort")
    executor_arg = _command_arg_value(args, "--executor-reasoning-effort")
    if planner_arg and executor_arg and planner_arg != executor_arg:
        return f"{planner_arg}_to_{executor_arg}"
    if executor_arg:
        return executor_arg
    if planner_arg:
        return planner_arg
    for names in (
        ("--reasoning-effort",),
    ):
        value = _command_arg_value(args, *names)
        if value:
            return value
    return None


def task_selection_label(config: dict[str, Any], final_result: dict[str, Any] | None = None) -> str:
    """Build a compact task/trial label for result filenames."""
    parts = [str(config.get("task_split", "split-unspecified"))]
    if "num_trials" in config:
        parts.append(f"trials{config['num_trials']}")

    split_abbreviations = {
        "base": "base",
        "hallucination": "hall",
        "disambiguation": "dis",
    }
    summary = final_result.get("summary", {}) if isinstance(final_result, dict) else {}
    actual_splits = summary.get("splits", {}) if isinstance(summary, dict) else {}

    for split, abbreviation in split_abbreviations.items():
        actual = actual_splits.get(split, {}) if isinstance(actual_splits, dict) else {}
        if isinstance(actual, dict) and "num_unique_tasks" in actual:
            parts.append(f"{abbreviation}{actual['num_unique_tasks']}")
            continue

        filter_key = f"tasks_{split}_task_id_filter"
        num_key = f"tasks_{split}_num_tasks"
        if filter_key in config and config[filter_key] is not None:
            value = config[filter_key]
            count = len(value) if isinstance(value, list) else 1
            parts.append(f"{abbreviation}{count}ids")
        elif num_key in config:
            value = config[num_key]
            parts.append(f"{abbreviation}{'all' if value == -1 else value}")

    if isinstance(summary, dict) and summary.get("num_results") is not None:
        parts.append(f"runs{summary['num_results']}")

    return "-".join(str(part) for part in parts)


def resolve_output_path(
    output_arg: str | None,
    scenario_path: Path,
    data: dict[str, Any],
    final_result: dict[str, Any] | None = None,
) -> Path | None:
    if not output_arg:
        return None

    output_path = Path(output_arg)
    if output_path.suffix == ".json":
        return output_path

    metadata = _agent_metadata(data)
    agent_slug = _slug(_agent_name(scenario_path, data), default="agent_under_test")
    scenario_slug = _slug(_scenario_name(scenario_path, data), default="scenario")
    filename_parts = [
        datetime.now().strftime("%Y%m%d-%H%M%S"),
        scenario_slug,
        _slug(task_selection_label(data.get("config", {}) or {}, final_result), default="tasks"),
    ]
    model_label = _model_label(metadata)
    reasoning_label = _reasoning_label(metadata)
    if model_label:
        filename_parts.append(_slug(model_label, default="model"))
    if reasoning_label:
        filename_parts.append(_slug(reasoning_label, default="reasoning"))
    filename = "__".join(filename_parts) + ".json"
    return output_path / agent_slug / filename


def build_output_payload(
    *,
    req: EvalRequest,
    evaluator_url: str,
    scenario_path: Path,
    scenario_data: dict[str, Any],
    artifact_records: list[dict[str, Any]],
    started_at: datetime,
    completed_at: datetime,
) -> dict[str, Any]:
    all_data_parts = [
        data
        for artifact in artifact_records
        for data in artifact.get("data_parts", [])
    ]
    final_result, final_summary = _find_final_result(artifact_records)
    metadata = _agent_metadata(scenario_data)
    model_label = _model_label(metadata)
    reasoning_label = _reasoning_label(metadata)
    raw_wall_time_seconds = (completed_at - started_at).total_seconds()
    quota_wait_seconds = _quota_wait_seconds_from_artifacts(
        final_result,
        artifact_records,
    )
    wall_time_seconds = max(0.0, raw_wall_time_seconds - quota_wait_seconds)

    return {
        "metadata": {
            "schema_version": 1,
            "started_at": started_at.isoformat(),
            "completed_at": completed_at.isoformat(),
            "wall_time_seconds": round(wall_time_seconds, 3),
            "raw_wall_time_seconds": round(raw_wall_time_seconds, 3),
            "quota_wait_seconds": round(quota_wait_seconds, 3),
            "scenario_path": str(scenario_path),
            "scenario_name": _scenario_name(scenario_path, scenario_data),
            "agent_name": _agent_name(scenario_path, scenario_data),
            "agent_under_test": str(req.agent_under_test),
            "evaluator": evaluator_url,
            "model": model_label,
            "reasoning_effort": reasoning_label,
            "task_selection": task_selection_label(
                scenario_data.get("config", {}) or {},
                final_result,
            ),
            "agent_metadata": metadata,
            "config": scenario_data.get("config", {}),
        },
        "summary_text": final_summary,
        "summary": final_result.get("summary", {}) if isinstance(final_result, dict) else {},
        "final_result": final_result,
        "results": all_data_parts,
        "artifacts": artifact_records,
    }


_STATE_NAMES = {
    TaskState.TASK_STATE_SUBMITTED: "submitted",
    TaskState.TASK_STATE_WORKING: "working",
    TaskState.TASK_STATE_COMPLETED: "completed",
    TaskState.TASK_STATE_FAILED: "failed",
    TaskState.TASK_STATE_CANCELED: "canceled",
    TaskState.TASK_STATE_INPUT_REQUIRED: "input-required",
    TaskState.TASK_STATE_REJECTED: "rejected",
    TaskState.TASK_STATE_AUTH_REQUIRED: "auth-required",
}


async def main():
    parser = argparse.ArgumentParser(description="Run a CAR-bench A2A scenario client.")
    parser.add_argument("scenario", type=Path, help="A2A scenario TOML.")
    parser.add_argument(
        "output",
        nargs="?",
        help=(
            "Output JSON file or directory. Directories receive timestamped "
            "files under <dir>/<agent-name>/."
        ),
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print all streaming messages and artifact contents.",
    )
    args = parser.parse_args()

    scenario_path = args.scenario
    output_arg = args.output

    if not scenario_path.exists():
        print(f"File not found: {scenario_path}")
        sys.exit(1)

    toml_data = scenario_path.read_text()
    data = tomllib.loads(toml_data)

    req, evaluator_url = parse_toml(data)
    started_at = datetime.now(timezone.utc)
    start_monotonic = time.perf_counter()

    # Collect artifacts from streaming events
    artifact_records = []

    # Send message via streaming
    organizer_token = os.environ.get("CAR_BENCH_ORGANIZER_TOKEN")
    client_headers = (
        {"X-CAR-BENCH-ORGANIZER-TOKEN": organizer_token}
        if organizer_token
        else None
    )
    async with httpx.AsyncClient(
        timeout=DEFAULT_TIMEOUT,
        headers=client_headers,
    ) as httpx_client:
        resolver = A2ACardResolver(httpx_client=httpx_client, base_url=evaluator_url)
        agent_card = await resolver.get_agent_card()
        config = ClientConfig(
            httpx_client=httpx_client,
            streaming=True,
        )
        factory = ClientFactory(config)
        client = factory.create(agent_card)

        outbound_msg = create_message(text=req.model_dump_json())
        request = SendMessageRequest(message=outbound_msg)

        try:
            async for event in client.send_message(request):
                payload_type = event.WhichOneof("payload")

                if payload_type == "message":
                    msg = event.message
                    if args.verbose:
                        print_parts(msg.parts)

                elif payload_type == "task":
                    task = event.task
                    state_name = _STATE_NAMES.get(task.status.state, "unknown")
                    parts = task.status.message.parts if task.status.message.parts else []
                    if args.verbose:
                        print_parts(parts, state_name)
                    if task.status.state == TaskState.TASK_STATE_COMPLETED:
                        artifact_records.extend(_parse_artifact(a) for a in task.artifacts)
                    elif task.status.state not in (
                        TaskState.TASK_STATE_SUBMITTED,
                        TaskState.TASK_STATE_WORKING,
                    ):
                        raise AgentFailedError(f"Agent returned status {state_name}.")

                elif payload_type == "status_update":
                    update = event.status_update
                    state_name = _STATE_NAMES.get(update.status.state, "unknown")
                    parts = update.status.message.parts if update.status.message.parts else []
                    if args.verbose:
                        print_parts(parts, state_name)
                    if update.status.state == TaskState.TASK_STATE_COMPLETED:
                        pass  # Artifacts come via artifact_update events
                    elif update.status.state not in (
                        TaskState.TASK_STATE_SUBMITTED,
                        TaskState.TASK_STATE_WORKING,
                    ):
                        raise AgentFailedError(f"Agent returned status {state_name}.")

                elif payload_type == "artifact_update":
                    update = event.artifact_update
                    if update.artifact:
                        if args.verbose:
                            print_parts(update.artifact.parts, "Artifact update")
                        artifact_records.append(_parse_artifact(update.artifact))

        except AgentFailedError as e:
            print(str(e))
            sys.exit(1)

    completed_at = datetime.now(timezone.utc)
    final_result, final_summary = _find_final_result(artifact_records)
    print_final_summary(final_result, final_summary)

    output_path = resolve_output_path(output_arg, scenario_path, data, final_result)
    if output_path:
        output_data = build_output_payload(
            req=req,
            evaluator_url=evaluator_url,
            scenario_path=scenario_path,
            scenario_data=data,
            artifact_records=artifact_records,
            started_at=started_at,
            completed_at=completed_at,
        )
        raw_client_wall_time_seconds = time.perf_counter() - start_monotonic
        quota_wait_seconds = _safe_float(
            output_data["metadata"].get("quota_wait_seconds", 0.0)
        )
        output_data["metadata"]["client_wall_time_seconds"] = round(
            max(0.0, raw_client_wall_time_seconds - quota_wait_seconds),
            3,
        )
        output_data["metadata"]["raw_client_wall_time_seconds"] = round(
            raw_client_wall_time_seconds,
            3,
        )
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(output_data, f, indent=2)
        print(f"\nResults written to {output_path}")


if __name__ == "__main__":
    asyncio.run(main())
