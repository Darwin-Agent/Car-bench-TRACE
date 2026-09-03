"""Cluster CAR-Bench trajectories by selected skill name."""

from __future__ import annotations

import argparse
import json
import re
import shutil
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


NO_SKILL_GROUP = "_no_selected_skill"
UNKNOWN_SKILL_GROUP = "_unknown_skill"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Read skill names from skills_bank, then group every trajectory in a "
            "CAR-Bench result JSON by the selected_skill_names found in assistant messages. "
            "One or more result JSON files can be provided."
        )
    )
    parser.add_argument("json_files", nargs="+", type=Path, help="CAR-Bench result JSON file(s)")
    parser.add_argument(
        "--skills-dir",
        type=Path,
        default=Path("skills_bank"),
        help="Directory containing */SKILL.md files. Default: skills_bank",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        help="Output directory. Default: output/skill_clusters/<first json file stem>",
    )
    parser.add_argument(
        "--formats",
        nargs="+",
        choices=("md", "jsonl"),
        default=("md", "jsonl"),
        help="Per-skill output formats. Default: md jsonl",
    )
    parser.add_argument(
        "--keep-existing",
        action="store_true",
        help="Do not remove an existing output directory before writing.",
    )
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)
    if not isinstance(data, dict):
        raise ValueError(f"{path}: top-level JSON value must be an object")
    return data


def load_skill_names(skills_dir: Path) -> list[str]:
    skill_names: list[str] = []
    for skill_file in sorted(skills_dir.glob("*/SKILL.md")):
        name = read_skill_name(skill_file) or skill_file.parent.name
        if name not in skill_names:
            skill_names.append(name)
    if not skill_names:
        raise ValueError(f"No */SKILL.md files found under {skills_dir}")
    return skill_names


def read_skill_name(skill_file: Path) -> str | None:
    in_frontmatter = False
    for line in skill_file.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped == "---":
            if not in_frontmatter:
                in_frontmatter = True
                continue
            break
        if in_frontmatter and line.startswith("name:"):
            return line.split(":", 1)[1].strip().strip("'\"")
    return None


def get_detailed_results(data: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    final_result = data.get("final_result")
    if isinstance(final_result, dict):
        detailed = final_result.get("detailed_results_by_split")
        if isinstance(detailed, dict):
            return normalize_detailed_results(detailed)

    for artifact in data.get("artifacts", []):
        if not isinstance(artifact, dict):
            continue
        for part in artifact.get("data_parts", []):
            if not isinstance(part, dict):
                continue
            detailed = part.get("detailed_results_by_split")
            if isinstance(detailed, dict):
                return normalize_detailed_results(detailed)
    return {}


def normalize_detailed_results(detailed: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    normalized: dict[str, list[dict[str, Any]]] = {}
    for split, items in detailed.items():
        if isinstance(items, list):
            normalized[str(split)] = [item for item in items if isinstance(item, dict)]
    return normalized


def unique_in_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result


def selected_skills(item: dict[str, Any]) -> list[str]:
    names: list[str] = []
    trajectory = item.get("trajectory")
    if not isinstance(trajectory, list):
        return names
    for message in trajectory:
        if not isinstance(message, dict):
            continue
        selected = message.get("selected_skill_names")
        if isinstance(selected, list):
            names.extend(name for name in selected if isinstance(name, str) and name)
    return unique_in_order(names)


def skill_source_counts(item: dict[str, Any]) -> dict[str, int]:
    counts: Counter[str] = Counter()
    trajectory = item.get("trajectory")
    if not isinstance(trajectory, list):
        return {}
    for message in trajectory:
        if isinstance(message, dict) and "selected_skill_source" in message:
            counts[str(message.get("selected_skill_source"))] += 1
    return dict(sorted(counts.items()))


def user_request(item: dict[str, Any]) -> str:
    trajectory = item.get("trajectory")
    if not isinstance(trajectory, list):
        return ""
    for message in trajectory:
        if isinstance(message, dict) and message.get("role") == "user":
            return content_to_text(message.get("content"))
    return ""


def final_assistant_message(item: dict[str, Any]) -> str:
    trajectory = item.get("trajectory")
    if not isinstance(trajectory, list):
        return ""
    for message in reversed(trajectory):
        if isinstance(message, dict) and message.get("role") == "assistant":
            content = message.get("content")
            if content is not None:
                return content_to_text(content)
    return ""


def called_tools(item: dict[str, Any]) -> list[str]:
    tools: list[str] = []
    trajectory = item.get("trajectory")
    if not isinstance(trajectory, list):
        return tools
    for message in trajectory:
        if not isinstance(message, dict):
            continue
        tool_calls = message.get("tool_calls")
        if isinstance(tool_calls, list):
            for call in tool_calls:
                if not isinstance(call, dict):
                    continue
                function = call.get("function")
                if isinstance(function, dict) and isinstance(function.get("name"), str):
                    tools.append(function["name"])
                elif isinstance(call.get("name"), str):
                    tools.append(call["name"])
        if message.get("role") == "tool" and isinstance(message.get("name"), str):
            tools.append(message["name"])
    return unique_in_order(tools)


def expected_actions(item: dict[str, Any]) -> list[str]:
    task = item.get("task")
    if not isinstance(task, dict):
        return []
    actions = task.get("actions")
    if not isinstance(actions, list):
        return []
    names: list[str] = []
    for action in actions:
        if isinstance(action, dict) and isinstance(action.get("name"), str):
            names.append(action["name"])
    return names


def reward_actions(item: dict[str, Any]) -> list[str]:
    reward_info = item.get("reward_info")
    if not isinstance(reward_info, dict):
        return []
    actions = reward_info.get("actions")
    if not isinstance(actions, list):
        return []
    names: list[str] = []
    for action in actions:
        if isinstance(action, dict) and isinstance(action.get("name"), str):
            names.append(action["name"])
    return names


def reward_info_value(item: dict[str, Any], key: str) -> Any:
    reward_info = item.get("reward_info")
    if not isinstance(reward_info, dict):
        return None
    info = reward_info.get("info")
    if not isinstance(info, dict):
        return None
    return info.get(key)


def build_record(
    item: dict[str, Any],
    split: str,
    result_index: int,
    matched_skills: list[str],
    unknown_skills: list[str],
    source_json: Path,
) -> dict[str, Any]:
    return {
        "source_json": str(source_json),
        "source_json_name": source_json.name,
        "split": split,
        "result_index": result_index,
        "task_id": item.get("task_id"),
        "trial": item.get("trial"),
        "reward": item.get("reward"),
        "error": item.get("error"),
        "user_request": user_request(item),
        "final_assistant_message": final_assistant_message(item),
        "matched_skill_names": matched_skills,
        "unknown_skill_names": unknown_skills,
        "selected_skill_names": selected_skills(item),
        "selected_skill_source_counts": skill_source_counts(item),
        "called_tools": called_tools(item),
        "expected_actions": expected_actions(item),
        "reward_actions": reward_actions(item),
        "tool_subset_missing_tools": reward_info_value(item, "tool_subset_missing_tools"),
        "policy_errors": reward_info_value(item, "policy_aut_errors"),
        "tool_execution_errors": reward_info_value(item, "tool_execution_errors"),
        "num_a2a_turns": item.get("num_a2a_turns"),
        "total_a2a_time_ms": item.get("total_a2a_time_ms"),
        "total_agent_cost": item.get("total_agent_cost"),
        "agent_total_tokens": item.get("agent_total_tokens"),
        "trajectory": item.get("trajectory"),
        "task": item.get("task"),
        "reward_info": item.get("reward_info"),
    }


def cluster_records(
    detailed: dict[str, list[dict[str, Any]]],
    skill_names: list[str],
    source_json: Path,
) -> tuple[dict[str, list[dict[str, Any]]], list[dict[str, Any]]]:
    skill_set = set(skill_names)
    groups: dict[str, list[dict[str, Any]]] = {name: [] for name in skill_names}
    groups[UNKNOWN_SKILL_GROUP] = []
    groups[NO_SKILL_GROUP] = []
    all_records: list[dict[str, Any]] = []

    for split, items in detailed.items():
        for result_index, item in enumerate(items):
            names = selected_skills(item)
            matched = [name for name in names if name in skill_set]
            unknown = [name for name in names if name not in skill_set]
            record = build_record(item, split, result_index, matched, unknown, source_json)
            all_records.append(record)

            if matched:
                for skill_name in matched:
                    groups[skill_name].append(record)
            if unknown:
                groups[UNKNOWN_SKILL_GROUP].append(record)
            if not names:
                groups[NO_SKILL_GROUP].append(record)

    return groups, all_records


def safe_filename(name: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", name).strip("._")
    return safe or "unnamed"


def short_text(text: Any, limit: int = 160) -> str:
    value = content_to_text(text).replace("\t", " ").replace("\n", " ").strip()
    if len(value) <= limit:
        return value
    return value[: limit - 1] + "…"


def content_to_text(content: Any) -> str:
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    return json.dumps(content, ensure_ascii=False, sort_keys=True)


def one_line_json(value: Any) -> str:
    if value in (None, [], {}):
        return ""
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def markdown_code(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True)


def role_label(message: dict[str, Any]) -> str:
    role = str(message.get("role", "unknown"))
    if role == "tool" and message.get("name"):
        return f"tool:{message['name']}"
    return role


def render_tool_calls(message: dict[str, Any]) -> str:
    tool_calls = message.get("tool_calls")
    if not isinstance(tool_calls, list) or not tool_calls:
        return ""
    rendered: list[str] = []
    for call in tool_calls:
        if not isinstance(call, dict):
            rendered.append(markdown_code(call))
            continue
        function = call.get("function")
        if isinstance(function, dict):
            name = function.get("name", "unknown_tool")
            arguments = function.get("arguments")
        else:
            name = call.get("name", "unknown_tool")
            arguments = call.get("arguments")
        rendered.append(f"- `{name}` args: `{content_to_text(arguments)}`")
    return "\n".join(rendered)


def render_trajectory(record: dict[str, Any]) -> str:
    trajectory = record.get("trajectory")
    if not isinstance(trajectory, list):
        return "_No trajectory found._\n"

    parts: list[str] = []
    for message_index, message in enumerate(trajectory, 1):
        if not isinstance(message, dict):
            parts.append(f"#### Message {message_index}: unknown\n\n```json\n{markdown_code(message)}\n```\n")
            continue
        selected = message.get("selected_skill_names")
        source = message.get("selected_skill_source")
        selected_text = ""
        if selected or source:
            selected_text = f"\n\nSelected skills: `{one_line_json(selected)}`; source: `{source}`"
        tool_calls = render_tool_calls(message)
        tool_text = f"\n\nTool calls:\n{tool_calls}" if tool_calls else ""
        content = content_to_text(message.get("content")) or "(no content)"
        parts.append(
            f"#### Message {message_index}: {role_label(message)}{selected_text}{tool_text}\n\n"
            f"```text\n{content}\n```\n"
        )
    return "\n".join(parts)


def write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as file:
        for record in records:
            file.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")


def write_skill_markdown(path: Path, skill_name: str, records: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as file:
        file.write(f"# {skill_name}\n\n")
        file.write(f"Total trajectories: {len(records)}\n\n")
        if not records:
            file.write("_No trajectories selected this skill._\n")
            return

        for index, record in enumerate(records, 1):
            task_id = record.get("task_id")
            split = record.get("split")
            trial = record.get("trial")
            reward = record.get("reward")
            file.write(f"## {index}. {split} / {task_id} / trial {trial} / reward {reward}\n\n")
            file.write(f"- Source JSON: `{record.get('source_json')}`\n")
            file.write(f"- Result index: `{record.get('result_index')}`\n")
            file.write(f"- User request: {short_text(record.get('user_request'), 500)}\n")
            file.write(f"- Final assistant: {short_text(record.get('final_assistant_message'), 500)}\n")
            file.write(f"- Matched skills: `{one_line_json(record.get('matched_skill_names'))}`\n")
            if record.get("unknown_skill_names"):
                file.write(f"- Unknown skills: `{one_line_json(record.get('unknown_skill_names'))}`\n")
            file.write(f"- Skill source counts: `{one_line_json(record.get('selected_skill_source_counts'))}`\n")
            file.write(f"- Called tools: `{one_line_json(record.get('called_tools'))}`\n")
            file.write(f"- Expected actions: `{one_line_json(record.get('expected_actions'))}`\n")
            file.write(f"- Reward actions: `{one_line_json(record.get('reward_actions'))}`\n")
            if record.get("tool_subset_missing_tools"):
                file.write(f"- Missing tools: `{one_line_json(record.get('tool_subset_missing_tools'))}`\n")
            if record.get("tool_execution_errors"):
                file.write(f"- Tool execution errors: `{one_line_json(record.get('tool_execution_errors'))}`\n")
            if record.get("policy_errors"):
                file.write(f"- Policy errors: `{one_line_json(record.get('policy_errors'))}`\n")
            file.write("\n")
            file.write("### Trajectory\n\n")
            file.write(render_trajectory(record))
            file.write("\n")


def write_summary(output_dir: Path, groups: dict[str, list[dict[str, Any]]]) -> None:
    summary_path = output_dir / "summary.tsv"
    with summary_path.open("w", encoding="utf-8") as file:
        file.write("skill_name\tnum_trajectories\tnum_success\tnum_failure\tavg_reward\ttask_ids\n")
        for skill_name, records in groups.items():
            rewards = [record.get("reward") for record in records if isinstance(record.get("reward"), (int, float))]
            successes = sum(1 for reward in rewards if float(reward) > 0)
            failures = sum(1 for reward in rewards if float(reward) <= 0)
            avg_reward = sum(float(reward) for reward in rewards) / len(rewards) if rewards else 0.0
            task_ids = sorted({str(record.get("task_id")) for record in records if record.get("task_id") is not None})
            file.write(
                f"{skill_name}\t{len(records)}\t{successes}\t{failures}\t{avg_reward:.3f}\t"
                f"{','.join(task_ids)}\n"
            )


def write_index(
    output_dir: Path,
    json_files: list[Path],
    skill_names: list[str],
    groups: dict[str, list[dict[str, Any]]],
    total_records: int,
) -> None:
    with (output_dir / "README.md").open("w", encoding="utf-8") as file:
        file.write("# Skill Trajectory Clusters\n\n")
        if len(json_files) == 1:
            file.write(f"Source JSON: `{json_files[0]}`\n\n")
        else:
            file.write("Source JSON files:\n\n")
            for json_file in json_files:
                file.write(f"- `{json_file}`\n")
            file.write("\n")
        file.write(f"Total result trajectories: {total_records}\n\n")
        file.write("## Files\n\n")
        file.write("- `summary.tsv`: one-line summary per skill group.\n")
        file.write("- `all_records.jsonl`: every trajectory once, with extracted metadata and raw trajectory.\n")
        file.write("- `*.md`: readable trajectories grouped by selected skill.\n")
        file.write("- `*.jsonl`: structured trajectories grouped by selected skill.\n\n")
        file.write("## Skill Groups\n\n")
        file.write("| Skill | Trajectories | Markdown | JSONL |\n")
        file.write("| --- | ---: | --- | --- |\n")
        for skill_name in skill_names + [UNKNOWN_SKILL_GROUP, NO_SKILL_GROUP]:
            records = groups.get(skill_name, [])
            filename = safe_filename(skill_name)
            file.write(
                f"| `{skill_name}` | {len(records)} | "
                f"[`{filename}.md`]({filename}.md) | [`{filename}.jsonl`]({filename}.jsonl) |\n"
            )


def prepare_output_dir(output_dir: Path, keep_existing: bool) -> None:
    if output_dir.exists() and not keep_existing:
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)


def main() -> None:
    args = parse_args()
    json_files = [json_file.expanduser().resolve() for json_file in args.json_files]
    skills_dir = args.skills_dir.expanduser().resolve()
    for json_file in json_files:
        if not json_file.is_file():
            raise SystemExit(f"JSON file not found: {json_file}")
    if not skills_dir.is_dir():
        raise SystemExit(f"Skills directory not found: {skills_dir}")

    output_dir = args.output_dir
    if output_dir is None:
        output_dir = Path("output") / "skill_clusters" / json_files[0].stem
    output_dir = output_dir.expanduser().resolve()

    skill_names = load_skill_names(skills_dir)
    groups: dict[str, list[dict[str, Any]]] = {name: [] for name in skill_names}
    groups[UNKNOWN_SKILL_GROUP] = []
    groups[NO_SKILL_GROUP] = []
    all_records: list[dict[str, Any]] = []

    for json_file in json_files:
        data = load_json(json_file)
        detailed = get_detailed_results(data)
        if not detailed:
            raise SystemExit(f"No detailed_results_by_split found in {json_file}")
        file_groups, file_records = cluster_records(detailed, skill_names, json_file)
        all_records.extend(file_records)
        for skill_name, records in file_groups.items():
            groups[skill_name].extend(records)

    prepare_output_dir(output_dir, args.keep_existing)
    write_summary(output_dir, groups)
    write_index(output_dir, json_files, skill_names, groups, len(all_records))
    write_jsonl(output_dir / "all_records.jsonl", all_records)

    for skill_name, records in groups.items():
        filename = safe_filename(skill_name)
        if "jsonl" in args.formats:
            write_jsonl(output_dir / f"{filename}.jsonl", records)
        if "md" in args.formats:
            write_skill_markdown(output_dir / f"{filename}.md", skill_name, records)

    print(f"Loaded {len(skill_names)} skills from {skills_dir}")
    print(f"Loaded {len(json_files)} JSON file(s)")
    print(f"Clustered {len(all_records)} trajectories into {output_dir}")
    print(f"Summary: {output_dir / 'summary.tsv'}")
    print(f"Index: {output_dir / 'README.md'}")


if __name__ == "__main__":
    main()
