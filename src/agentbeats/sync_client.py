"""Synchronous client for A2A communication - safe to use in thread pools.

Uses v1.0 JSON-RPC format with protobuf-compatible JSON serialization.
"""
import json
import os
from uuid import uuid4

import httpx
from a2a.types import Message, Role, Task
from google.protobuf.json_format import MessageToDict, ParseDict


DEFAULT_TIMEOUT = float(os.getenv("CAR_BENCH_A2A_TIMEOUT_SECONDS", "86400"))

# A2A v1.0 headers
A2A_HEADERS = {
    "Content-Type": "application/a2a+json",
    "A2A-Version": "1.0",
}


def create_message_with_parts(*, role: int = Role.ROLE_USER, parts: list, context_id: str | None = None, task_id: str | None = None, metadata: dict | None = None) -> Message:
    """Create a protobuf Message with given parts."""
    msg = Message(
        role=role,
        message_id=uuid4().hex,
    )
    if context_id:
        msg.context_id = context_id
    if task_id:
        msg.task_id = task_id
    if metadata:
        msg.metadata.update(metadata)
    for part in parts:
        msg.parts.append(part)
    return msg


def merge_parts(parts) -> str:
    """Extract text content from a list of protobuf Parts."""
    chunks = []
    for part in parts:
        content_type = part.WhichOneof("content")
        if content_type == "text":
            chunks.append(part.text)
        elif content_type == "data":
            chunks.append(json.dumps(MessageToDict(part.data), indent=2))
    return "\n".join(chunks)


def build_send_message_jsonrpc_request(message: Message) -> dict:
    """Build an A2A 1.0 JSON-RPC SendMessage request.

    Use protobuf's default JSON mapping so public field names are lowerCamelCase
    (`messageId`, `contextId`, etc.), matching the SDK's own JSON-RPC transport.
    """
    return {
        "jsonrpc": "2.0",
        "id": uuid4().hex,
        "method": "SendMessage",
        "params": {
            "message": MessageToDict(message),
        },
    }


def send_message_with_parts_sync(parts: list, base_url: str, context_id: str | None = None, task_id: str | None = None, metadata: dict | None = None) -> dict:
    """Send a message with custom parts synchronously. Safe for use in thread pools.

    Returns dict with context_id, task_id, response and status (if exists)
    """
    # Create the protobuf message
    outbound_msg = create_message_with_parts(parts=parts, context_id=context_id, task_id=task_id, metadata=metadata)
    jsonrpc_request = build_send_message_jsonrpc_request(outbound_msg)

    # Use synchronous httpx client
    with httpx.Client(timeout=DEFAULT_TIMEOUT) as client:
        response = client.post(
            base_url,
            json=jsonrpc_request,
            headers=A2A_HEADERS,
        )
        response.raise_for_status()

        result = response.json()

        if "error" in result:
            raise RuntimeError(f"JSON-RPC error: {result['error']}")

        response_data = result.get("result", {})

        # Parse the response based on type
        outputs = {
            "response": "",
            "context_id": None,
            "task_id": None,
            "raw_message": None,
            "raw_artifacts": [],
        }

        # v1.0 wraps in SendMessageResponse with "message" or "task" key
        if "message" in response_data:
            msg = ParseDict(response_data["message"], Message())
            outputs["context_id"] = msg.context_id or None
            outputs["task_id"] = msg.task_id or None
            outputs["response"] = merge_parts(msg.parts)
            outputs["raw_message"] = msg
        elif "task" in response_data:
            task = ParseDict(response_data["task"], Task())
            outputs["context_id"] = task.context_id or None
            outputs["task_id"] = task.id or None
            if task.status and task.status.state:
                state_name = TaskState_to_string(task.status.state)
                outputs["status"] = state_name
            if task.status and task.status.message and task.status.message.parts:
                outputs["response"] = merge_parts(task.status.message.parts)
                outputs["raw_message"] = task.status.message
            if task.artifacts:
                for artifact in task.artifacts:
                    outputs["response"] += merge_parts(artifact.parts)
                    outputs["raw_artifacts"].append(artifact)

        return outputs


def TaskState_to_string(state: int) -> str:
    """Convert protobuf TaskState enum to a human-readable string."""
    from a2a.types import TaskState
    _map = {
        TaskState.TASK_STATE_SUBMITTED: "submitted",
        TaskState.TASK_STATE_WORKING: "working",
        TaskState.TASK_STATE_COMPLETED: "completed",
        TaskState.TASK_STATE_FAILED: "failed",
        TaskState.TASK_STATE_CANCELED: "canceled",
        TaskState.TASK_STATE_INPUT_REQUIRED: "input-required",
        TaskState.TASK_STATE_REJECTED: "rejected",
        TaskState.TASK_STATE_AUTH_REQUIRED: "auth-required",
    }
    return _map.get(state, f"unknown({state})")
