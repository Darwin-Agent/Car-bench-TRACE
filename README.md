# CAR-bench Skill-Bank Agent — Darwin Agent Team

## IJCAI-ECAI 2026 Competition Track 1

<p align="center">
<a href="https://car-bench.github.io/car-bench/leaderboard.html"><img src="https://img.shields.io/badge/🏆-1st_Place-gold?style=flat" alt="1st Place"></a>
<a href="https://darwin-agent.github.io/Car-bench-TRACE/"><img src="https://img.shields.io/badge/Homepage-Visit-ff6900?style=flat" alt="Homepage"></a>
<a href="https://arxiv.org/abs/2608.22793"><img src="https://img.shields.io/badge/Paper-arXiv-red?style=flat" alt="Paper"></a>
</p>

This repository contains Darwin Agent Team's solution for Track 1 of the IJCAI-ECAI 2026 CAR-bench Competition. It builds on the original [CAR-bench](https://github.com/CAR-bench/car-bench-ijcai) project and improves agent reliability on complex and uncertain in-car voice tasks by constructing a reusable domain-knowledge skill bank.

## Overview

The CAR-bench evaluator simulates the user, maintains vehicle and environment state, exposes tools, executes tool calls, and calculates benchmark scores. The Track 1 agent interprets policies and user requests, maintains conversation state for each `context_id`, retrieves relevant skills, and returns either user-facing text or tool calls.

```text
CAR-bench evaluator
  ├─ policy and user messages
  ├─ available tools
  └─ tool results
          │ A2A messages
          ▼
Track 1 agent
  ├─ per-context conversation history
  ├─ skill selector
  ├─ selected-skill injection
  └─ LiteLLM model response or tool calls
```

The agent never executes CAR-bench tools directly. It returns tool-call requests through A2A, and the evaluator executes them and sends the results back on the next turn. This preserves the evaluation boundary defined by the original project.

## Environment Setup

The project requires Python 3.11+ and uv. First create and activate a Python environment:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
```

Prepare the original CAR-bench repository with the provided script:

```bash
./setup_car_bench.sh
```

Install the dependencies required by the Track 1 agent, evaluator, and skill optimizer:

```bash
uv sync \
  --extra track-1-agent \
  --extra car-bench-evaluator \
  --extra skill-optimizer
```

Configure the model credentials required by the evaluator and agent in your shell or a local `.env` file. For example:

```bash
GEMINI_API_KEY=...
OPENAI_API_KEY=...
```

## Testing and Skill-Bank Evolution

![TRACE](assets/trace.png)

### Skill Bank

The repository provides two reproducible and comparable skill-bank versions:

- `skills_bank_v0/`: the initial skill bank.
- `skills_bank/`: the final skill bank after trajectory-driven optimization.

Each skill is stored in a dedicated directory containing a `SKILL.md` file. The agent first gives the model a compact skill index. The model selects up to five relevant skills, and their full instructions are then injected into the system context for the next response.

### Public Test Set

The repository currently provides the Track 1 public test-set scenario:

```bash
uv run car-bench-run \
  scenarios/track_1_agent_under_test/local_test_set.toml \
  --show-logs
```

Results are written under `output/` by default. The task count, number of trials, evaluator model, and agent model can be adjusted in the scenario TOML file.

### Skill-Bank Evolution

The skill evolution workflow uses the Claude Agent SDK. Before running the evolution scripts, install the corresponding optional dependency and configure the credentials required by the Claude Agent SDK in environment variables or a local `.env` file:

```bash
uv sync --extra skill-optimizer
```

#### 1. Cluster trajectories by selected skill usage

```bash
python skill_optimizer/cluster_trajectories_by_skill.py output/track_1_agent_under_test/xxx.json \
  --skills-dir skills_bank_v0 \
  --output-dir output/skill_clusters/run
```

Common parameters:

- `--skills-dir`: the skill-bank directory used to match skill names, usually the pre-iteration version.
- `--output-dir`: the output directory for clustered trajectory results.

The script reads selected skill names from trajectory records and writes one cluster of records per skill. It also preserves records in which no skill was selected, making it easier to analyze whether additional skills are needed.

#### 2. Optimize the existing skill bank from clustered trajectories

```bash
python skill_optimizer/optimizer.py output/skill_clusters/run --skills-dir skills_bank_v0
```

Common parameters:

- `output/skill_clusters/run`: the trajectory-cluster directory generated in the previous step.
- `--skills-dir`: the skill bank directory to optimize. The optimizer directly edits the `SKILL.md` files in this directory.
- `--filter-all-success-tasks`: filter tasks whose trials all succeeded to reduce unnecessary optimization.
- `--keep-first-success`: for tasks whose trials all succeeded, keep one successful trajectory as a reference.

The optimizer first formats trajectories and groups them by task, then calls the Claude Agent SDK to analyze trajectories and modify the corresponding `SKILL.md` files.

## Citation

If you find this work useful, please cite:

```bibtex
@article{wu2026trace,
  title   = {{TRACE}: A Self-Evolving Skill Bank for Consistent, Limit-Aware {LLM} Agents},
  author  = {Wenhao Wu and Menghao Zhang and Xin Wang and Zhi Wang and Kun Shao and Jian Luan},
  year    = {2026},
  journal = {arXiv preprint arXiv:2608.22793}
}
```
