"""Format per-skill CAR-Bench trajectories for later skill optimization.

The script reads skill names from ``skills_bank``, finds the corresponding
clustered trajectory files under an experiment directory, groups records by
task, and writes an English structured text file per skill.
"""
from __future__ import annotations

from dotenv import find_dotenv, load_dotenv
load_dotenv(find_dotenv())
import argparse
import asyncio
from claude_agent_sdk import ClaudeAgentOptions, query
from claude_agent_sdk.types import ResultMessage
from pathlib import Path
from tqdm import tqdm
from typing import Any

from utils import (
    filter_all_success_task_trajectories,
    find_no_selected_skill_record_file,
    find_skill_record_file,
    group_records_by_task,
    load_records,
    load_skill_files,
    prepare_output_dir,
    reflow_skill_file,
    render_no_selected_skill_records,
    render_skill_records,
    safe_filename,
    skill_inventory_text,
    success_value,
    write_index,
    NO_SELECTED_SKILL_STEM,
    SKILL_WRITING_GUIDE
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Read skill names from skills_bank, then format each skill's "
            "clustered trajectories into task-grouped English text."
        )
    )
    parser.add_argument(
        "cluster_dir",
        type=Path,
        help="Directory containing per-skill .jsonl/.json trajectory files.",
    )
    parser.add_argument(
        "--skills-dir",
        type=Path,
        default=Path("skills_bank"),
        help="Directory containing */SKILL.md files. Default: skills_bank",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        help=(
            "Output directory. Default: <cluster_dir>/formatted_for_optimization"
        ),
    )
    parser.add_argument(
        "--delete-existing",
        action="store_true",
        help="Remove an existing output directory before writing.",
    )
    parser.add_argument(
        "--include-stop",
        action="store_true",
        help="Include trailing ###STOP### user messages in the formatted text.",
    )
    parser.add_argument(
        "--exclude-planning-tools",
        action="store_true",
        help="Exclude planning_tool and think from reconstructed available tools.",
    )
    parser.add_argument(
        "--skip-skill-optimization",
        action="store_true",
        help="Only format per-skill trajectories; do not ask Claude to edit existing skills.",
    )
    parser.add_argument(
        "--filter-all-success-tasks",
        action="store_true",
        help=(
            "For tasks whose trajectories all succeeded, drop the whole task "
            "before formatting unless --keep-first-success is also set."
        ),
    )
    parser.add_argument(
        "--keep-first-success",
        action="store_true",
        help=(
            "When --filter-all-success-tasks is set, keep the first successful "
            "trajectory as a reference instead of dropping the whole task."
        ),
    )
    parser.add_argument(
        "--skip-no-skill-analysis",
        action="store_true",
        help="Do not analyze no_selected_skill trajectories for possible new skills.",
    )
    return parser.parse_args()


def optimize_skill_from_formatted_trajectories(
    skill_name: str,
    formatted_text: str,
    records: list[dict[str, Any]],
    skill_file: Path,
) -> list | None:
    """Use the Claude Code/Agent SDK to optimize the matching skill file.

    The function asks Claude to inspect the successful and failed trajectories,
    infer general lessons, and directly edit ``skill_file``. The prompt forbids
    copying hidden task metadata or user-only context into the skill.
    """
    if not records:
        return None
    assert skill_file.is_file(), f"Skill file not found: {skill_file}"
    system_prompt = build_skill_optimization_system_prompt(skill_name, skill_file)
    messages = asyncio.run(run_claude_skill_optimization(system_prompt, formatted_text, cwd=Path.cwd()))
    reflow_skill_file(skill_file)
    return messages


def analyze_no_selected_skill_trajectories(
    formatted_text: str,
    records: list[dict[str, Any]],
    skills_dir: Path,
    existing_skills_text: str,
) -> list | None:
    """Ask Claude to decide whether no-skill trajectories need new skills."""
    if not records:
        return None
    assert skills_dir.is_dir(), f"Skills directory not found: {skills_dir}"
    system_prompt = build_no_selected_skill_creation_system_prompt(skills_dir, existing_skills_text)
    messages = asyncio.run(run_claude_skill_optimization(system_prompt, formatted_text, cwd=Path.cwd()))
    for skill_md in skills_dir.glob("*/SKILL.md"):
        reflow_skill_file(skill_md)
    return messages


def build_skill_optimization_system_prompt(skill_name: str, skill_file: Path) -> str:
    return f"""You are optimizing one skill for CAR-Bench performance.

Skill name: {skill_name}
Skill file to edit directly: {skill_file}

The user prompt contains formatted trajectories from tasks that selected this skill. Some succeeded and some failed. Analyze the successful and failed trajectories to identify general behavioral patterns, missing guidance, over-broad guidance, wrong tool ordering, hallucination risks, clarification mistakes, and capability-boundary issues. Then edit the SKILL.md file directly to improve future performance.

# Hard constraints:
- Edit only this skill file: {skill_file}, or create a new skill file.
- Do not hard-wrap prose. Write each paragraph, sentence, or list item as a single physical line without inserting manual line breaks; only break lines at real paragraph boundaries (a blank line) or list items.
- Do not mention, copy, or encode task IDs in the skill.
- Do not mention task split/type labels such as base, hallucination, disambiguation, or any equivalent benchmark-internal category.
- Do not assume a tool is usable just because it appears in a trajectory or base tool set. Teach the assistant to verify what is actually available (callable tools, present arguments) and to read results honestly before claiming completion: an "unknown" response field is a masked value to obtain elsewhere or surface, not a real or fabricated one.
- Do not phrase guidance around a specific named tool, parameter, or response field being "removed", "missing", or "masked"; never enumerate which ones might be affected. Write capability-boundary guidance in general, observable terms instead: if you cannot call a tool needed to complete the requested function, or a needed value is unavailable, obtain it another legitimate way or tell the user plainly you cannot complete that part rather than guessing or fabricating.

{SKILL_WRITING_GUIDE}

# Note regarding user-provided information
- A single user conversation may involve several kinds of operations and thus draw on multiple skills; focus your analysis on the parts of each trajectory that are relevant to this skill, and do not rewrite this skill around behavior that belongs to a different one.
- In the formatted trajectories, the "## Instruction and Settings for User" section (including its "### Instruction" and "### User Context" subsections) contains hidden user intent/persona information. This information is only for your offline analysis of why each trajectory succeeded or failed. It is NOT visible to the assistant at runtime. Never write user persona, hidden intent, age, conversation style, or other hidden context into SKILL.md.
- The document-level "## System Prompt" and "## Tools Set for Assistant" sections contain the shared system prompt template and base tool schemas visible to the assistant at runtime. They are shown once and apply to every task. Each task then has "### System Prompt (Delta)" (the CURRENT_LOCATION and DATETIME placeholder values filled into the shared template for that task) and "### Tools Set for Assistant (Delta)". The tool delta can list up to three kinds of change, each with different runtime consequences: (1) removed tools, which are not callable for that task; (2) removed tool input parameters, where the tool is still callable but that argument is gone from its schema; and (3) masked tool response fields, where the tool is callable and the call succeeds, but at runtime the named field of the response comes back as the literal value "unknown" instead of its real value. A task's actual runtime affordances are the shared base set adjusted by these deltas. Use them to reason about actual policy/tool affordances, but do not copy long prompt or schema text into SKILL.md.

# Output expectations:
- First read the current SKILL.md so your edits preserve the existing style and structure.
- Apply the edit directly to SKILL.md using the available file-editing tools.
- If this skill turns out to cover too many distinct operation types, you may split it into multiple skills — keep this file focused on one operation and create a new skill directory (with its own SKILL.md) for each separate operation.
- In your final response, summarize the main changes and mention the edited path.
"""


def build_no_selected_skill_creation_system_prompt(skills_dir: Path, existing_skills_text: str) -> str:
    return f"""You are analyzing CAR-Bench trajectories where no skill was selected.

The user prompt contains formatted no-skill trajectories. Your job is to decide whether these trajectories reveal one or more missing reusable skills. If a clear reusable skill is missing, create it under:
{skills_dir}

# Existing skills:
{existing_skills_text}

# Decision criteria:
- Create a new skill only when multiple trajectories reveal a coherent, reusable pattern that is not already covered by an existing skill.
- Do not create a skill for one-off behavior, benchmark artifacts, or a pattern that should be handled by improving an existing skill.
- If an existing skill should cover the pattern, edit the existing skills accordingly.
- Keep each new skill focused on a single operation. It is acceptable to create more than one skill only if the trajectories clearly contain separate reusable domains — create a separate skill (its own directory and SKILL.md) per operation rather than one skill spanning several.

# Hard constraints for any new skill:
- Create files only inside {skills_dir}.
- Each new skill must be a directory named with a concise kebab-case skill name and must contain a SKILL.md file with valid YAML frontmatter including name and description.
- Do not mention, copy, or encode task IDs in the skill.
- Do not mention task split/type labels such as base, hallucination, disambiguation, no-selected-skill, or any equivalent benchmark-internal category.
- Do not write benchmark-specific examples that reveal private task wording or hidden evaluation data. Convert observations into general reusable guidance.
- Do not assume a tool is usable just because it appears in a trajectory. Teach the assistant to verify what is actually available (callable tools, present arguments) and to interpret tool results honestly before claiming completion: an "unknown" response field is a masked value to obtain elsewhere or surface, not a real or fabricated one.
- Do not phrase guidance around a specific named tool, parameter, or response field being "removed", "missing", or "masked"; never enumerate which ones might be affected. Write capability-boundary guidance in general, observable terms instead: if you cannot call a tool needed to complete the requested function, or a needed value is unavailable, obtain it another legitimate way or tell the user plainly you cannot complete that part rather than guessing or fabricating.
- Keep SKILL.md concise and general. Prefer durable rules over memorized examples.
- Do not hard-wrap prose. Write each paragraph, sentence, or list item as a single physical line without inserting manual line breaks; only break lines at real paragraph boundaries (a blank line) or list items.

{SKILL_WRITING_GUIDE}

# Note regarding user-provided information
- A single user conversation may involve several kinds of operations and thus draw on multiple skills; focus your analysis on the parts of each trajectory that reveal a coherent, reusable gap, and judge each candidate operation separately rather than bundling unrelated ones into a single new skill.
- In the formatted trajectories, the "## Instruction and Settings for User" section (including its "### Instruction" and "### User Context" subsections) contains hidden user intent/persona information. This information is only for offline analysis of why each trajectory succeeded or failed. It is NOT visible to the assistant at runtime. Never write user persona, hidden intent, age, conversation style, or other hidden context into SKILL.md.
- The document-level "## System Prompt" and "## Tools Set for Assistant" sections contain the shared system prompt template and base tool schemas visible to the assistant at runtime. They are shown once and apply to every task. Each task then has "### System Prompt (Delta)" (the CURRENT_LOCATION and DATETIME placeholder values filled into the shared template for that task) and "### Tools Set for Assistant (Delta)". The tool delta can list up to three kinds of change, each with different runtime consequences: (1) removed tools, which are not callable for that task; (2) removed tool input parameters, where the tool is still callable but that argument is gone from its schema; and (3) masked tool response fields, where the tool is callable and the call succeeds, but at runtime the named field of the response comes back as the literal value "unknown" instead of its real value. A task's actual runtime affordances are the shared base set adjusted by these deltas. Use them to reason about actual policy/tool affordances, but do not copy long prompt or schema text into SKILL.md.

# Output expectations:
- First inspect the existing skills list above and create new skill files only if justified by the trajectories.
- If creating a skill, write the SKILL.md directly using the available file tools.
- In your final response, state one of:
  1. "Created new skill(s): ..." with paths, or
  2. "No new skill needed" with a concise reason and any existing skill that has been modified.
"""


async def run_claude_skill_optimization(system_prompt: str, prompt: str, cwd: Path) -> list:
    options_kwargs: dict[str, Any] = dict(
        system_prompt={
            "type": "preset",
            "preset": "claude_code",
            "append": system_prompt,
        },
        tools=["Read", "Write", "Edit", "MultiEdit"],
        allowed_tools=["Read", "Write", "Edit", "MultiEdit"],
        cwd=str(cwd),
        permission_mode="dontAsk",
        thinking={"type": "adaptive"},
        effort="high",
    )
    options = ClaudeAgentOptions(**options_kwargs)
    messages: list[str] = []
    async for message in query(prompt=prompt, options=options):
        messages.append(message)
    return messages


def main() -> None:
    args = parse_args()
    cluster_dir = args.cluster_dir.expanduser().resolve()
    skills_dir = args.skills_dir.expanduser().resolve()
    output_dir = args.output_dir
    if output_dir is None:
        output_dir = cluster_dir / "formatted_for_optimization"
    output_dir = output_dir.expanduser().resolve()

    assert cluster_dir.is_dir(), f"Cluster directory not found: {cluster_dir}"
    assert skills_dir.is_dir(), f"Skills directory not found: {skills_dir}"

    skill_files = load_skill_files(skills_dir)
    skill_names = list(skill_files)
    prepare_output_dir(output_dir, args.delete_existing)

    index_rows: list[tuple[str, Path | None, int, int, Path | None]] = []
    written = 0
    missing = 0

    for skill_name in tqdm(skill_names, ncols=100):
        output_path: Path = output_dir / f"{safe_filename(skill_name)}.txt"
        if output_path.exists():
            tqdm.write(f"Skip {skill_name} as it already exists.")
            continue

        record_file = find_skill_record_file(cluster_dir, skill_name)
        if record_file is None:
            missing += 1
            index_rows.append((skill_name, None, 0, 0, None))
            tqdm.write(f"Skip {skill_name} as it is not found.")
            continue

        records = load_records(record_file)
        if args.filter_all_success_tasks:
            records = filter_all_success_task_trajectories(records, args.keep_first_success)
        formatted_text = render_skill_records(
            skill_name,
            records,
            include_stop=args.include_stop,
            include_planning_tools=not args.exclude_planning_tools,
        )
        no_records_after_filtering = len(records) == 0
        all_successful = all(success_value(record) for record in records) if records else False
        messages = None
        if not args.skip_skill_optimization and records and not all_successful:
            messages = optimize_skill_from_formatted_trajectories(
                skill_name,
                formatted_text,
                records,
                skill_files[skill_name],
            )
        elif no_records_after_filtering:
            tqdm.write(f"Skip optimizing {skill_name} as no trajectories remain after filtering.")
        elif all_successful:
            tqdm.write(f"Skip optimizing {skill_name} as all remaining trajectories succeeded.")

        output_path.write_text(formatted_text, encoding="utf-8")
        if messages and isinstance(messages[-1], ResultMessage):
            with output_path.open("a", encoding="utf-8") as file:
                file.write(f"\n\nClaude Code Output:\n{messages[-1].result}\n")
        task_count = len(group_records_by_task(records))
        index_rows.append((skill_name, record_file, task_count, len(records), output_path))
        written += 1
        tqdm.write(f"Complete analysing {skill_name}.")

    # After analyzing the trajectories for all skills, some trajectories did not use any skill. Next, analyze those trajectories to decide whether new skills need to be created.
    no_skill_record_file = find_no_selected_skill_record_file(cluster_dir)
    if no_skill_record_file is not None:
        no_skill_records = load_records(no_skill_record_file)
        no_skill_formatted_text = render_no_selected_skill_records(
            no_skill_records,
            include_stop=args.include_stop,
            include_planning_tools=not args.exclude_planning_tools,
        )
        no_skill_output_path = output_dir / f"{NO_SELECTED_SKILL_STEM}.txt"
        no_skill_output_path.write_text(no_skill_formatted_text, encoding="utf-8")
        if not args.skip_no_skill_analysis:
            messages = analyze_no_selected_skill_trajectories(
                no_skill_formatted_text,
                no_skill_records,
                skills_dir,
                skill_inventory_text(skill_files),
            )
            if messages and isinstance(messages[-1], ResultMessage):
                with no_skill_output_path.open("a", encoding="utf-8") as file:
                    file.write(f"\n\nClaude Code Output:\n{messages[-1].result}\n")
        index_rows.append((NO_SELECTED_SKILL_STEM, no_skill_record_file, len(group_records_by_task(no_skill_records)), len(no_skill_records), no_skill_output_path))

    write_index(output_dir, cluster_dir, index_rows)
    print(f"Loaded {len(skill_names)} skills from {skills_dir}")
    print(f"Wrote {written} formatted skill files to {output_dir}")
    if missing:
        print(f"Skipped {missing} skills without .jsonl/.json files in {cluster_dir}")
    print(f"Index: {output_dir / 'README.md'}")


if __name__ == "__main__":
    main()
