"""Shared tool-call data structures for the CAR-bench A2A contract.

Agents under test return CAR-bench tool calls in an A2A data Part shaped like:

    {"tool_calls": [{"tool_name": "...", "arguments": {...}}]}

These Pydantic models keep that payload consistent across the baseline, Codex,
planner/executor, and Python-call reference agents.
"""

from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel, Field


class ToolCall(BaseModel):
    """A single CAR-bench tool call embedded in an A2A data Part."""

    tool_name: str = Field(description="The name of the tool to call.")
    arguments: dict[str, Any] = Field(description="The arguments to pass to the tool.")

    def __str__(self) -> str:
        return f"ToolCall(tool_name={self.tool_name}, arguments={json.dumps(self.arguments)})"


class ToolCallsData(BaseModel):
    """Machine-readable tool-call payload returned by an agent under test."""

    tool_calls: list[ToolCall] = Field(description="List of tool calls to execute.")

    def __str__(self) -> str:
        return "ToolCallsData([" + ", ".join(str(tc) for tc in self.tool_calls) + "])"
