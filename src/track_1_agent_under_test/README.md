# Track 1 Agent

This package contains our IJCAI-ECAI 2026 Competition Track 1 solution. It
implements the A2A boundary expected by CAR-bench and adds a skill-bank-based
harness on top of the model client.

## Solution Flow

- Parse evaluator messages into policy/user text, tool definitions, and tool
  results.
- Maintain conversation history per `context_id`.
- Use one model call to select up to five relevant skills from the skill index.
- Inject the selected skill instructions into the system context for the next
  response.
- Ask the configured LiteLLM-compatible model for a user response and/or tool
  calls. The evaluator remains responsible for executing CAR-bench tools.

The runtime skill bank is selected with `CAR_BENCH_SKILLS_BANK_DIR`; it defaults
to the repository's `skills_bank/` directory. The initial version is kept in
`skills_bank_v0/` for comparison and reproduction.

## A2A Turn Contract

| Turn situation | Evaluator sends | Agent returns |
| --- | --- | --- |
| First task turn | Policy/user text and available tool definitions | Text and/or `{"tool_calls": [...]}` |
| After tool calls | Tool results | Text and/or more tool calls |
| After text response | Next simulated user message | Text and/or tool calls |

For exact message shapes, see the [development guide](../../docs/development-guide.md).

## Configuration

Set the model provider credentials in the shell or `.env` file. For example:

```bash
GEMINI_API_KEY=...
AGENT_LLM=anthropic/claude-haiku-4-5-20251001
ANTHROPIC_API_KEY=...
```

`AGENT_LLM` accepts any LiteLLM-compatible model string. `AGENT_API_MODE`,
`AGENT_TEMPERATURE`, and `AGENT_REASONING_EFFORT` are optional settings. Keep
the A2A input/output contract unchanged when replacing the model client.

## Run Locally

```bash
uv run car-bench-run scenarios/track_1_agent_under_test/local_smoke.toml --show-logs
uv run car-bench-run scenarios/track_1_agent_under_test/local_test_set.toml --show-logs
```

Use smoke runs while iterating, then run the public test set for comparison.
The public test set is development validation; it is not an organizer hidden
set.

## Read More

- [Main README](../../README.md): solution overview and reproduction steps.
- [Development guide](../../docs/development-guide.md): detailed A2A contract.
- [Harnessing guide](../../docs/agent-under-test-harnessing.md): allowed
  internal harness patterns.
