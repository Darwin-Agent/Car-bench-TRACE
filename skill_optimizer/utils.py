"""Utilities for formatting CAR-Bench skill trajectory files."""
from __future__ import annotations

import ast
import copy
import json
import re
import sys
from collections import OrderedDict
from pathlib import Path
from typing import Any


NO_SELECTED_SKILL_STEM = "no_selected_skill"
CAR_BENCH_THIRD_PARTY_DIR = Path(__file__).resolve().parents[1] / "third_party" / "car-bench"

# "How to write a good SKILL.md" guidance for the skill optimizer, adapted from the
# skill-creator skill's writing-guide sections to this scenario: each CAR-Bench skill
# is a single self-contained SKILL.md (no resources or scripts to point to), retrieved
# by its description, and must teach the three judgement dimensions (do-it-right /
# ask-vs-infer / honest-when-missing). The skill-creator's eval/benchmark/viewer
# workflow — which needs subagents, a browser, and Bash — is intentionally omitted.
# Embedded here so the model gets the authoring guidance without loading the heavyweight
# Skill tool.
SKILL_WRITING_GUIDE = """# How to write a good SKILL.md

In this scenario every skill is a **single self-contained `SKILL.md`** — there are no extra resources, scripts, or reference files to split content into or point at. One in-car-assistant operation (e.g. "set the climate temperature", "change the navigation destination", "open the headlights") gets one file. The file is a *general, reusable operating guide for that kind of request* — which tools to use, in what order, and the judgement that separates a good outcome from a bad one — **not** an answer key for any specific task.

## Anatomy of the file

```
skill-name/
└── SKILL.md (the only file)
    ├── YAML frontmatter: name, description, tools
    └── Markdown body (the method, it MUST be less than **60** lines)
```

- **name**: a concise kebab-case identifier for the operation (matches the directory name).
- **description**: the single most important field — see "How retrieval works" below.
- **compatibility**: Required tools, dependencies (optional, rarely needed)
- **the rest of the skill :)**

## How retrieval works (write the description for this)

The skill is selected by matching the user's latest request against the **description** — that one line is the entire basis for retrieval, so it carries the whole "when to use this" load. Write it to do two jobs at once:

1. **Name the trigger surface.** Lead with what the operation is and the phrasings/contexts that should pull it in, so a relevant request reliably matches. Claude tends to *under*-trigger skills, so lean slightly pushy: enumerate the natural ways a user expresses this operation rather than a single narrow phrase. But keep each skill's description to *its own* operation — overlapping, greedy descriptions across sibling skills cause the wrong one to win. Distinguish near-neighbours explicitly (e.g. setting a temperature vs. turning AC on vs. seat heating are different skills).
2. **Compress the method's judgement.** Because the body is only loaded after the skill is selected, pack the description with the decisions that matter most: how to handle explicit vs. relative vs. preference-fixed values, when to act vs. ask, and the honest-failure stance when a capability is missing. A good description reads like a one-sentence summary of the whole method.

Do **not** put hidden user/persona context, task ids, or any benchmark-internal vocabulary in the description (or anywhere). The description describes the *operation*, never a particular task.

## The three judgement dimensions every skill must teach

A single request can demand any combination of these, so each `SKILL.md` body must cover all three. This is the core of what makes the skill useful — most failures come from getting one of these wrong.

1. **Do it right (clear request).** When the request is unambiguous and the tools are present, execute exactly what was asked — the correct tool call(s), in the correct order, with any required precondition (e.g. read the current value before a relative change) — then stop. Don't over-act, fan out to a whole family of tools, or act-then-undo.
2. **Ask vs. infer (under-specified request).** When the user leaves something out:
   - **Infer silently — do NOT ask** when the missing piece is fixed by something the assistant can read for itself: a **stored preference**, the **current state/context**, or a **clear heuristic** the request implies ("just pick a route" → fastest). Asking "which one?" here is itself the failure. And when the context already contains the value (the user already said "level 3"), just act — never re-ask what was stated, and read a deciding value **once** rather than looping.
   - **Ask the user — do NOT guess** when the missing piece is a genuine choice only the user can make (a percentage, a direction, which of several windows, which route/person) and no preference/state/heuristic pins it. Inventing a value is the failure.
3. **Honest when a capability is missing.** Never fake success, invent data, or call a tool that will error. A capability can be absent three ways, each with its own honest response: a **whole tool missing** → say you have no control for that action and name the adjacent capability you DO retain; a **required parameter unavailable** → state the specific limitation and don't invoke the erroring call; a **read field returning `"unknown"`** → treat it as genuinely unverifiable (never assume it means zero/closed/off, never re-read in a loop expecting a value). In every case: **fulfil the doable parts, refuse only the impossible part, in one answer**, and surface a workaround or the value the user would need.

## Mine successes and failures in both directions

You are given both successful and failed trajectories for the operation, and they carry complementary lessons — capture both. The **successful** trajectories show the *key factors that produced a good outcome*: the right tool ordering, the precondition read that made a relative change correct, the point where the assistant inferred silently instead of asking, the honest partial answer that still satisfied the user. Distil these into **positive guidance** in the Method and Principles (what to do, and why it works) so the skill teaches the winning behaviour directly. The **failed** trajectories show what went wrong; turn each distinct failure into a concrete Common-mistakes entry. The strongest skills pair an important success factor with the mistake it prevents — the positive rule and its negative mirror reinforce each other.

## Body structure that works

Match the existing skills' shape — it has proven effective and keeps the bank consistent. A typical body, in order:

- A one-line framing of the operation and that the same method handles the clear / under-specified / missing-capability variants.
- **## When this applies** — the kinds of request that map here, and a pointer distinguishing sibling skills (so the reader confirms they're in the right place).
- **## Tools** — each whitelisted tool with its argument vocabulary, what it reads or changes, its ordering dependency, and explicitly which ones may be missing or return `"unknown"`.
- **## Method** — numbered steps for the happy path (the tool ordering and preconditions the successful trajectories share).
- **### Ask vs. infer** and **### When a capability is missing** — the two judgement subsections spelled out for this operation.
- **## Principles** — the durable rules behind the steps, including the key success factors distilled from the successful trajectories.
- **## Common mistakes to avoid** — the concrete failure modes (these are high-value: they're the difference between a method that's read and one that's followed).
- **## Procedure** — a tight, executable restatement of the steps with the actual tool calls.

Keep it focused and readable — long is fine when the judgement genuinely needs it (the existing skills run well past 100 lines), but every line should earn its place. There is no second file to defer detail to, so the body must be complete on its own.

## What must NOT go in the file (de-hardcoding policy)

These skills must stay legitimate general procedures, never lookup tables or answer keys. Exclude:
- **Specific answers or values as "the solution."** Values appear only as placeholders (`<the value the user gives>`, `<the level in the preference>`, `current ± N`) or as *categories* of valid options — never a concrete number/name as the answer.
- **Concrete environment identifiers** — no location/route/POI/contact/plug ids, phone numbers, emails, person names, or place/city names used as data. These are resolved at runtime from tools, never memorised.
- **Any request→answer mapping**, task ids, task type/split labels, or evaluation-internal vocabulary (reward/score/grader/ground-truth/trial/pass-fail).
- **Hidden user/persona context** — age, intent, conversation style, or anything from the offline-only "Instruction and Settings for User" sections.

What the file SHOULD contain is general and safe: tool names and their argument/enum vocabulary (the assistant has these tools at runtime anyway), the dependency order between calls, and behavioural principles for acting well, asking-vs-inferring correctly, and being honest when a capability is missing.

## Writing style

Prefer the imperative. Explain *why* a rule matters rather than stacking heavy-handed MUSTs — the model follows guidance it understands. Use theory of mind: write for an assistant that will see only this file plus the live request, not the trajectories you analysed. Keep the guidance general to the operation, not narrow to the examples you happened to see. Draft it, then reread with fresh eyes and tighten.

## Principle of lack of surprise

Skills must not contain malware, exploit code, or anything that could compromise security, and their contents should not surprise the user relative to their stated intent. Don't create misleading skills or skills designed to facilitate unauthorized access or data exfiltration."""


def unwrap_markdown_hard_wraps(text: str) -> str:
    """Join soft-wrapped prose lines in a Markdown document into single lines.

    Claude tends to hard-wrap body paragraphs at ~80-100 columns. This collapses
    those soft wraps back into one physical line per paragraph while leaving
    structural lines untouched: YAML frontmatter, fenced code blocks, headings,
    list items, tables, blockquotes, and blank lines all stay as-is. Paragraph
    breaks (blank lines) are preserved.
    """
    lines = text.split("\n")
    out: list[str] = []
    in_code_fence = False
    fence_marker = ""
    in_frontmatter = False
    # Frontmatter only counts if the very first line is the opening fence.
    if lines and lines[0].strip() in ("---", "+++"):
        in_frontmatter = True
        out.append(lines[0])
        start = 1
    else:
        start = 0

    list_item_re = re.compile(r"^(?P<indent>\s*)(?P<marker>[-*+]|\d+[.)])\s")
    # A hard break flushes the current joinable block and is emitted verbatim.
    hard_break_re = re.compile(r"^\s*(#{1,6}\s|>\s?|\|)")
    hr_re = re.compile(r"^\s*([-*_])\1{2,}\s*$")

    # The current joinable block: either a wrapped prose paragraph or a single
    # wrapped list item. Continuation prose lines are appended and joined.
    buffer: list[str] = []
    buffer_list_indent: int | None = None

    def flush_buffer() -> None:
        nonlocal buffer_list_indent
        if buffer:
            # Preserve indentation only for list items (including nested
            # lists). Plain prose paragraphs should not inherit incidental
            # indentation from a preceding list item.
            indent = " " * buffer_list_indent if buffer_list_indent is not None else ""
            joined = " ".join(part.strip() for part in buffer)
            out.append(indent + joined)
            buffer.clear()
        buffer_list_indent = None

    i = start
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        if in_frontmatter:
            out.append(line)
            if stripped in ("---", "+++"):
                in_frontmatter = False
            i += 1
            continue

        # Fenced code blocks (``` or ~~~), possibly indented.
        fence_match = re.match(r"^(\s*)(`{3,}|~{3,})", line)
        if fence_match:
            marker = fence_match.group(2)[:3]
            if not in_code_fence:
                flush_buffer()
                in_code_fence = True
                fence_marker = marker
            elif marker == fence_marker:
                in_code_fence = False
                fence_marker = ""
            out.append(line)
            i += 1
            continue

        if in_code_fence:
            out.append(line)
            i += 1
            continue

        # Blank line, headings, blockquotes, tables, horizontal rules: a hard
        # boundary that ends the current joinable block and is kept verbatim.
        if stripped == "" or hard_break_re.match(line) or hr_re.match(line):
            flush_buffer()
            out.append(line)
            i += 1
            continue

        # A new list item starts a new joinable block.
        list_item_match = list_item_re.match(line)
        if list_item_match:
            flush_buffer()
            buffer.append(line)
            buffer_list_indent = len(list_item_match.group("indent"))
            i += 1
            continue

        if buffer_list_indent is not None:
            line_indent = len(line) - len(line.lstrip())
            if line_indent <= buffer_list_indent:
                flush_buffer()

        # Plain prose: a continuation of the current paragraph, or of the most
        # recent list item only when it is indented deeper than that list item.
        buffer.append(line)
        i += 1

    flush_buffer()
    result = "\n".join(out)
    if text.endswith("\n") and not result.endswith("\n"):
        result += "\n"
    return result


def reflow_skill_file(skill_file: Path) -> None:
    """Rewrite a SKILL.md in place, collapsing hard-wrapped prose paragraphs."""
    if not skill_file.is_file():
        return
    original = skill_file.read_text(encoding="utf-8")
    reflowed = unwrap_markdown_hard_wraps(original)
    if reflowed != original:
        skill_file.write_text(reflowed, encoding="utf-8")


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


def read_skill_description(skill_file: Path) -> str:
    in_frontmatter = False
    for line in skill_file.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped == "---":
            if not in_frontmatter:
                in_frontmatter = True
                continue
            break
        if in_frontmatter and line.startswith("description:"):
            return line.split(":", 1)[1].strip().strip("'\"")
    return ""


def load_skill_names(skills_dir: Path) -> list[str]:
    skill_names: list[str] = []
    for skill_file in sorted(skills_dir.glob("*/SKILL.md")):
        name = read_skill_name(skill_file) or skill_file.parent.name
        if name not in skill_names:
            skill_names.append(name)
    assert skill_names, f"No */SKILL.md files found under {skills_dir}"
    return skill_names


def load_skill_files(skills_dir: Path) -> OrderedDict[str, Path]:
    skill_files: OrderedDict[str, Path] = OrderedDict()
    for skill_file in sorted(skills_dir.glob("*/SKILL.md")):
        name = read_skill_name(skill_file) or skill_file.parent.name
        if name not in skill_files:
            skill_files[name] = skill_file
    assert skill_files, f"No */SKILL.md files found under {skills_dir}"
    return skill_files


def skill_inventory_text(skill_files: OrderedDict[str, Path]) -> str:
    lines: list[str] = []
    for name, skill_file in skill_files.items():
        description = read_skill_description(skill_file)
        suffix = f" — {description}" if description else ""
        lines.append(f"- {name}: {skill_file}{suffix}")
    return "\n".join(lines)


def safe_filename(name: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", name).strip("._")
    return safe or "unnamed"


def load_records(path: Path) -> list[dict[str, Any]]:
    if path.suffix == ".jsonl":
        records: list[dict[str, Any]] = []
        with path.open("r", encoding="utf-8") as file:
            for line_number, line in enumerate(file, 1):
                if not line.strip():
                    continue
                value = json.loads(line)
                assert isinstance(value, dict), (
                    f"{path}:{line_number}: JSONL records must be objects"
                )
                records.append(value)
        return records

    with path.open("r", encoding="utf-8") as file:
        value = json.load(file)
    if isinstance(value, list):
        return [item for item in value if isinstance(item, dict)]
    if isinstance(value, dict):
        for key in ("records", "trajectories", "items", "data"):
            items = value.get(key)
            if isinstance(items, list):
                return [item for item in items if isinstance(item, dict)]
        return [value]
    assert False, f"{path}: expected a JSON object or list"


def find_skill_record_file(cluster_dir: Path, skill_name: str) -> Path | None:
    stem = safe_filename(skill_name)
    candidates = [
        cluster_dir / f"{stem}.jsonl",
        cluster_dir / f"{stem}.json",
        cluster_dir / f"{skill_name}.jsonl",
        cluster_dir / f"{skill_name}.json",
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return None


def find_no_selected_skill_record_file(cluster_dir: Path) -> Path | None:
    for suffix in (".jsonl", ".json"):
        candidate = cluster_dir / f"{NO_SELECTED_SKILL_STEM}{suffix}"
        if candidate.is_file():
            return candidate
    return None


def content_to_text(content: Any) -> str:
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    return json.dumps(content, ensure_ascii=False, sort_keys=True)


def parse_json_string(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return value


def compact_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def pretty_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True)


def fenced_json(value: Any) -> list[str]:
    return ["```json", pretty_json(value), "```"]


def load_car_bench_system_prompt() -> str | None:
    """Load the CAR-Bench wiki prompt sent as the first system prompt."""
    wiki_path = CAR_BENCH_THIRD_PARTY_DIR / "car_bench" / "envs" / "car_voice_assistant" / "wiki.md"
    assert wiki_path.is_file()
    wiki_raw = wiki_path.read_text(encoding="utf-8")
    system_prompt = (
        wiki_raw.replace("INS:", "")
        .replace("AUT-POL:", "")
        .replace("LLM-POL:", "")
    )
    return system_prompt


def load_car_bench_tools_info() -> list[dict[str, Any]] | None:
    """Load tool schemas as CARBenchAgentExecutor receives them from the evaluator."""
    added_path = False
    third_party_path = str(CAR_BENCH_THIRD_PARTY_DIR)
    if CAR_BENCH_THIRD_PARTY_DIR.is_dir() and third_party_path not in sys.path:
        sys.path.insert(0, third_party_path)
        added_path = True
    from car_bench.envs.car_voice_assistant.tools import ALL_TOOLS
    if added_path:
        sys.path.remove(third_party_path)

    tool_info = [tool.get_info() for tool in ALL_TOOLS]
    return copy.deepcopy(tool_info)


def load_car_bench_tools_info_static() -> list[dict[str, Any]] | None:
    """Read ALL_TOOLS get_info() dictionaries without importing CAR-Bench."""
    tools_init_path = (
        CAR_BENCH_THIRD_PARTY_DIR
        / "car_bench"
        / "envs"
        / "car_voice_assistant"
        / "tools"
        / "__init__.py"
    )
    if not tools_init_path.is_file():
        return None

    try:
        tree = ast.parse(tools_init_path.read_text(encoding="utf-8"))
    except SyntaxError:
        return None

    class_to_path: dict[str, Path] = {}
    lists: dict[str, list[str]] = {}
    for node in tree.body:
        if isinstance(node, ast.ImportFrom) and node.module:
            module_path = tools_init_path.parent / Path(*node.module.split("."))
            module_path = module_path.with_suffix(".py")
            for alias in node.names:
                class_to_path[alias.asname or alias.name] = module_path
        elif isinstance(node, ast.Assign):
            names = list_assignment_names(node.value, lists)
            if names is None:
                continue
            for target in node.targets:
                if isinstance(target, ast.Name):
                    lists[target.id] = names

    tool_class_names = lists.get("ALL_TOOLS")
    if not tool_class_names:
        return None

    tools_info: list[dict[str, Any]] = []
    for class_name in tool_class_names:
        tool_path = class_to_path.get(class_name)
        if tool_path is None:
            return None
        tool_info = read_static_get_info(tool_path, class_name)
        if tool_info is None:
            return None
        tools_info.append(tool_info)
    return tools_info


def list_assignment_names(value: ast.AST, lists: dict[str, list[str]]) -> list[str] | None:
    if isinstance(value, ast.List):
        names: list[str] = []
        for element in value.elts:
            if not isinstance(element, ast.Name):
                return None
            names.append(element.id)
        return names
    if isinstance(value, ast.Name):
        return list(lists.get(value.id, []))
    if isinstance(value, ast.BinOp) and isinstance(value.op, ast.Add):
        left = list_assignment_names(value.left, lists)
        right = list_assignment_names(value.right, lists)
        if left is None or right is None:
            return None
        return left + right
    return None


def read_static_get_info(tool_path: Path, class_name: str) -> dict[str, Any] | None:
    try:
        tree = ast.parse(tool_path.read_text(encoding="utf-8"))
    except (OSError, SyntaxError):
        return None

    for node in tree.body:
        if not isinstance(node, ast.ClassDef) or node.name != class_name:
            continue
        for item in node.body:
            if not isinstance(item, ast.FunctionDef) or item.name != "get_info":
                continue
            for statement in item.body:
                if isinstance(statement, ast.Return):
                    try:
                        value = ast.literal_eval(statement.value)
                    except (ValueError, TypeError, SyntaxError):
                        return None
                    return value if isinstance(value, dict) else None
    return None


def remove_tool_parameter_at_path(tool: dict[str, Any], param_path: list[str]) -> None:
    current = tool.get("function", {}).get("parameters", {})
    if not current or "properties" not in current:
        return

    for part in param_path[:-1]:
        properties = current.get("properties", {})
        current = properties.get(part, {})
        if not isinstance(current, dict):
            return

    properties = current.get("properties", {})
    if param_path[-1] in properties:
        del properties[param_path[-1]]

    required = current.get("required")
    if isinstance(required, list) and param_path[-1] in required:
        current["required"] = [item for item in required if item != param_path[-1]]


def remove_tool_elements(tools_info: list[dict[str, Any]], removals: list[Any] | None) -> list[dict[str, Any]]:
    modified_tools = copy.deepcopy(tools_info)
    if not removals:
        return modified_tools

    for removal in removals:
        if not isinstance(removal, str) or not removal:
            continue
        parts = removal.split(".")
        tool_name = parts[0]
        if len(parts) == 1:
            modified_tools = [
                tool
                for tool in modified_tools
                if tool.get("function", {}).get("name") != tool_name
            ]
            continue
        for tool in modified_tools:
            if tool.get("function", {}).get("name") == tool_name:
                remove_tool_parameter_at_path(tool, parts[1:])
                break
    return modified_tools


def task_context_init_config(record: dict[str, Any]) -> dict[str, Any]:
    task = record.get("task")
    if not isinstance(task, dict):
        return {}
    context_config = task.get("context_init_config")
    return context_config if isinstance(context_config, dict) else {}


# Placeholder tokens in the CAR-Bench wiki system prompt, mapped to the wiki
# variable names they sit next to (CURRENT_LOCATION = {{...location...}},
# DATETIME = {{...datetime...}}) and the context_init_config keys that fill them.
SYSTEM_PROMPT_PLACEHOLDERS: tuple[tuple[str, str], ...] = (
    ("CURRENT_LOCATION", "current_location"),
    ("DATETIME", "current_datetime"),
)


def base_tools_info(*, include_planning_tools: bool = True) -> list[dict[str, Any]]:
    """Return the base tool set shared by all tasks, before per-task removals.

    Only the global planning-tool switch is applied here. Per-task removals from
    ``task.removed_part`` are reported separately as a delta on each task block.
    """
    tools_info = load_car_bench_tools_info()
    if not include_planning_tools:
        tools_info = remove_tool_elements(tools_info, ["planning_tool", "think"])
    return tools_info


def record_removed_part(record: dict[str, Any]) -> list[str]:
    """Return the per-task tool/parameter removals declared in ``task.removed_part``."""
    task = record.get("task")
    if not isinstance(task, dict):
        return []
    removed_part = task.get("removed_part")
    if not isinstance(removed_part, list):
        return []
    return [item for item in removed_part if isinstance(item, str) and item]


def classify_removed_part(removals: list[str]) -> "OrderedDict[str, list[str]]":
    """Split ``removed_part`` specs into CAR-Bench's three removal kinds.

    Mirrors how CAR-Bench's orchestrator interprets each dot-notation spec:
    - "tool_name" — the whole tool is removed from the schema (not callable).
    - "tool_name.param[.sub...]" — an input parameter is removed from the tool schema; the tool stays callable but that argument is gone.
    - "result.tool_name.field[...]" — the tool stays callable and succeeds, but that field of its response is replaced with the literal value "unknown" at runtime.
    """
    classified: OrderedDict[str, list[str]] = OrderedDict(
        removed_tools=[], removed_params=[], masked_result_fields=[]
    )
    for spec in removals:
        parts = spec.split(".")
        if parts[0] == "result":
            classified["masked_result_fields"].append(spec)
        elif len(parts) == 1:
            classified["removed_tools"].append(spec)
        else:
            classified["removed_params"].append(spec)
    return classified


def record_placeholder_values(record: dict[str, Any]) -> "OrderedDict[str, Any]":
    """Return per-task system-prompt placeholder values, keyed by wiki variable name.

    These mirror the placeholders CAR-Bench's run.py fills into the shared system
    prompt template: CURRENT_LOCATION and DATETIME.
    """
    context_config = task_context_init_config(record)
    values: OrderedDict[str, Any] = OrderedDict()
    for name, config_key in SYSTEM_PROMPT_PLACEHOLDERS:
        values[name] = context_config.get(config_key)
    return values


def render_shared_runtime_sections(*, include_planning_tools: bool = True) -> list[str]:
    """Render the shared system prompt template and base tool set once per document."""
    system_prompt = load_car_bench_system_prompt().strip()
    tools_info = base_tools_info(include_planning_tools=include_planning_tools)
    assert system_prompt and tools_info

    lines: list[str] = [
        '# System Prompt (shared template; the CURRENT_LOCATION and DATETIME placeholders below are filled per task with the values shown under each task\'s "System Prompt (Delta)")',
        "```text",
        system_prompt,
        "```",
        "",
        '# Tools Set for Assistant (shared base set; each task may remove specific tools or parameters, listed under that task\'s "Tools Set for Assistant (Delta)")',
        f"Tool count: {len(tools_info)}",
    ]
    lines.extend(fenced_json(tools_info))
    lines.append("")
    return lines


def render_task_runtime_deltas(record: dict[str, Any]) -> list[str]:
    """Render per-task deltas: placeholder values and removed tools/parameters."""
    lines: list[str] = ["## System Prompt (Delta)"]
    for name, value in record_placeholder_values(record).items():
        if value is None:
            lines.append(f"{name} = (not provided; placeholder left unfilled)")
        else:
            lines.append(f"{name} = {json.dumps(value, ensure_ascii=False, sort_keys=True)}")
    lines.append("")

    lines.append("## Tools Set for Assistant (Delta)")
    classified = classify_removed_part(record_removed_part(record))
    removed_tools = classified["removed_tools"]
    removed_params = classified["removed_params"]
    masked_result_fields = classified["masked_result_fields"]
    if not removed_tools and not removed_params and not masked_result_fields:
        lines.append("No changes from the base tool set; tools behave as defined in the shared base set.")
    else:
        if removed_tools:
            lines.append(f"Tools unavailable (not unavailable for this task): {', '.join(removed_tools)}")
        if removed_params:
            lines.append(f"Tool input parameters unavailable (tool still callable, but this argument is unavailable from its schema): {', '.join(removed_params)}")
        if masked_result_fields:
            masked = ", ".join(spec.split(".", 1)[1] for spec in masked_result_fields)
            lines.append(f'Masked tool response fields (tool is callable and the call succeeds, but at runtime this field of the response is returned as the literal value "unknown" rather than its real value): {masked}')
    lines.append("")
    return lines


def render_tool_calls(message: dict[str, Any]) -> str:
    calls = message.get("tool_calls") or message.get("tool_calls_converted") or []
    lines: list[str] = []
    for call in calls:
        if not isinstance(call, dict):
            continue
        function = call.get("function") or {}
        name = call.get("name") or function.get("name") or call.get("tool_name") or "tool"
        arguments = (
            call.get("arguments")
            or call.get("args")
            or function.get("arguments")
            or call.get("input")
            or {}
        )
        arguments = parse_json_string(arguments)
        lines.append(f"Tool call: {name}({compact_json(arguments)})")
    return "\n".join(lines)


def render_tool_result(message: dict[str, Any]) -> str:
    name = message.get("name") or message.get("tool_name") or "tool"
    result = (
        message.get("content")
        or message.get("result")
        or message.get("output")
        or message.get("tool_result")
    )
    result = parse_json_string(result)
    return f"Tool result ({name}): {content_to_text(result)}"


def render_assistant_message(message: dict[str, Any]) -> str:
    parts: list[str] = []
    content = content_to_text(message.get("content") or message.get("text"))
    if content:
        parts.append(content)
    tool_calls = render_tool_calls(message)
    if tool_calls:
        parts.append(tool_calls)
    return "\n".join(parts)


def render_trajectory_messages(trajectory: Any, *, include_stop: bool = False) -> list[str]:
    if not isinstance(trajectory, list):
        return [f"Trajectory: {content_to_text(trajectory)}"]

    lines: list[str] = []
    for index, message in enumerate(trajectory, 1):
        if not isinstance(message, dict):
            lines.append(f"Message {index}: {content_to_text(message)}")
            continue
        role = str(message.get("role") or message.get("type") or "message").lower()
        content = content_to_text(message.get("content") or message.get("text"))
        if role == "user" and not include_stop and content.strip() == "###STOP###":
            continue
        if role == "assistant":
            rendered = render_assistant_message(message)
        elif role in {"tool", "function"} or message.get("tool_result") is not None:
            rendered = render_tool_result(message)
        else:
            rendered = content
        if rendered:
            lines.append(f"{role.capitalize()}: {rendered}")
    return lines


def task_instruction(record: dict[str, Any]) -> str:
    return record.get("task", {}).get("instruction", "")


def task_persona(record: dict[str, Any]) -> str:
    return record.get("task", {}).get("persona", "")


def task_failure_reason(record: dict[str, Any]) -> str:
    return record.get("task", {}).get("failure_reason", "")


def success_value(record: dict[str, Any]) -> int:
    return int(record.get("reward"))


def group_records_by_task(records: list[dict[str, Any]]) -> OrderedDict[str, list[dict[str, Any]]]:
    grouped: OrderedDict[str, list[dict[str, Any]]] = OrderedDict()
    for record in records:
        task_id = record.get("task_id")
        task_key = content_to_text(task_id)
        grouped.setdefault(task_key, []).append(record)
    return grouped


def filter_all_success_task_trajectories(
    records: list[dict[str, Any]],
    keep_first_success: bool = True,
) -> list[dict[str, Any]]:
    """Drop redundant trajectories from tasks whose every trajectory succeeded.

    For each task, if all of its trajectories are successful, either keep only
    the first one as a reference or drop the task entirely depending on
    ``keep_first_success``. Tasks with at least one failed trajectory are left
    untouched. Task grouping and the relative order of the kept records follow
    ``group_records_by_task``.
    """
    grouped = group_records_by_task(records)
    filtered: list[dict[str, Any]] = []
    for task_records in grouped.values():
        if all(success_value(record) for record in task_records):
            if keep_first_success:
                filtered.append(task_records[0])
        else:
            filtered.extend(task_records)
    return filtered


def render_task_block(
    task_index: int,
    task_id: str,
    task_records: list[dict[str, Any]],
    *,
    include_stop: bool,
) -> list[str]:
    first_record = task_records[0]
    lines: list[str] = [
        f"# Task {task_index}",
        "",
        "## Instruction and Settings for User",
        "This is not available to assistant.",
        "",
        "### Instruction",
        task_instruction(first_record),
        "",
        "### User Context",
        task_persona(first_record),
        "",
    ]
    if task_failure_reason(first_record):
        lines.append("## Reasons for Failure (Ignore this if the trajectories below are successful)")
        lines.append(task_failure_reason(first_record))
        lines.append("")
    lines.extend(render_task_runtime_deltas(first_record))
    lines.append("## Trajectories")
    lines.append("")

    for trajectory_index, record in enumerate(task_records, 1):
        lines.append(
            f"### Trajectory {trajectory_index} "
            f"(Success: {success_value(record)})"
        )
        lines.extend(render_trajectory_messages(record.get("trajectory"), include_stop=include_stop))
        lines.append("")

    lines.append("---")
    lines.append("")
    return lines


def render_skill_records(
    skill_name: str,
    records: list[dict[str, Any]],
    *,
    include_stop: bool,
    include_planning_tools: bool = True,
) -> str:
    grouped = group_records_by_task(records)
    lines: list[str] = [
        f"# Skill trajectory summary: {skill_name}",
        "",
        f"Total trajectories: {len(records)}",
        f"Total tasks: {len(grouped)}",
        "",
        "---",
        "",
    ]
    lines.extend(render_shared_runtime_sections(include_planning_tools=include_planning_tools))
    lines.append("---")
    lines.append("")

    for task_index, (task_id, task_records) in enumerate(grouped.items(), 1):
        lines.extend(
            render_task_block(
                task_index,
                task_id,
                task_records,
                include_stop=include_stop,
            )
        )

    return "\n".join(lines).rstrip() + "\n"


def render_no_selected_skill_records(records: list[dict[str, Any]], *, include_stop: bool, include_planning_tools: bool = True) -> str:
    grouped = group_records_by_task(records)
    lines: list[str] = [
        "# No-skill trajectory summary",
        "",
        f"Total trajectories: {len(records)}",
        f"Total tasks: {len(grouped)}",
        "",
        "---",
        "",
    ]
    lines.extend(render_shared_runtime_sections(include_planning_tools=include_planning_tools))
    lines.append("---")
    lines.append("")

    for task_index, (task_id, task_records) in enumerate(grouped.items(), 1):
        lines.extend(
            render_task_block(
                task_index,
                task_id,
                task_records,
                include_stop=include_stop,
            )
        )

    return "\n".join(lines).rstrip() + "\n"


def prepare_output_dir(output_dir: Path, delete_existing: bool) -> None:
    if output_dir.exists() and delete_existing:
        import shutil
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)


def write_index(
    output_dir: Path,
    cluster_dir: Path,
    rows: list[tuple[str, Path | None, int, int, Path | None]],
) -> None:
    index_path = output_dir / "README.md"
    with index_path.open("w", encoding="utf-8") as file:
        file.write("# Formatted Skill Trajectories\n\n")
        file.write(f"Source cluster directory: `{cluster_dir}`\n\n")
        file.write("| Skill | Source File | Tasks | Trajectories | Output |\n")
        file.write("| --- | --- | ---: | ---: | --- |\n")
        for skill_name, source_path, task_count, record_count, output_path in rows:
            source = f"`{source_path.name}`" if source_path else "missing"
            output = f"`{output_path.name}`" if output_path else "-"
            file.write(
                f"| `{skill_name}` | {source} | {task_count} | "
                f"{record_count} | {output} |\n"
            )
