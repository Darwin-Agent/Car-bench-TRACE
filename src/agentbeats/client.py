import json
import logging
import os
from uuid import uuid4

import httpx
from a2a.client import (
    A2ACardResolver,
    ClientConfig,
    ClientFactory,
)
from a2a.types import (
    Message,
    Role,
    SendMessageRequest,
    StreamResponse,
)
from a2a.helpers.proto_helpers import new_text_part
from google.protobuf.json_format import MessageToDict


DEFAULT_TIMEOUT = float(os.getenv("CAR_BENCH_A2A_TIMEOUT_SECONDS", "86400"))


def create_message(*, role: int = Role.ROLE_USER, text: str, context_id: str | None = None) -> Message:
    msg = Message(
        role=role,
        message_id=uuid4().hex,
    )
    if context_id:
        msg.context_id = context_id
    msg.parts.append(new_text_part(text))
    return msg


def create_message_with_parts(*, role: int = Role.ROLE_USER, parts: list, context_id: str | None = None, task_id: str | None = None) -> Message:
    """Create a protobuf Message with custom parts."""
    msg = Message(
        role=role,
        message_id=uuid4().hex,
    )
    if context_id:
        msg.context_id = context_id
    if task_id:
        msg.task_id = task_id
    for part in parts:
        msg.parts.append(part)
    return msg


def merge_parts(parts) -> str:
    chunks = []
    for part in parts:
        content_type = part.WhichOneof("content")
        if content_type == "text":
            chunks.append(part.text)
        elif content_type == "data":
            chunks.append(json.dumps(MessageToDict(part.data), indent=2))
    return "\n".join(chunks)


async def send_message(message: str, base_url: str, context_id: str | None = None, task_id: str | None = None, streaming=False):
    """Returns dict with context_id, task_id, response and status (if exists)"""
    async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as httpx_client:
        resolver = A2ACardResolver(httpx_client=httpx_client, base_url=base_url)
        agent_card = await resolver.get_agent_card()
        config = ClientConfig(
            httpx_client=httpx_client,
            streaming=streaming,
        )
        factory = ClientFactory(config)
        client = factory.create(agent_card)

        outbound_msg = create_message(text=message, context_id=context_id)
        if task_id:
            outbound_msg.task_id = task_id

        request = SendMessageRequest(message=outbound_msg)

        outputs = {
            "response": "",
            "context_id": None,
            "task_id": None,
        }

        async for event in client.send_message(request):
            payload_type = event.WhichOneof("payload")

            if payload_type == "message":
                msg = event.message
                outputs["context_id"] = msg.context_id or None
                outputs["task_id"] = msg.task_id or None
                outputs["response"] += merge_parts(msg.parts)

            elif payload_type == "task":
                task = event.task
                outputs["context_id"] = task.context_id or None
                outputs["task_id"] = task.id or None
                if task.status and task.status.state:
                    from a2a.types import TaskState
                    state_map = {
                        TaskState.TASK_STATE_COMPLETED: "completed",
                        TaskState.TASK_STATE_FAILED: "failed",
                        TaskState.TASK_STATE_WORKING: "working",
                        TaskState.TASK_STATE_SUBMITTED: "submitted",
                        TaskState.TASK_STATE_CANCELED: "canceled",
                        TaskState.TASK_STATE_INPUT_REQUIRED: "input-required",
                        TaskState.TASK_STATE_REJECTED: "rejected",
                        TaskState.TASK_STATE_AUTH_REQUIRED: "auth-required",
                    }
                    outputs["status"] = state_map.get(task.status.state, "unknown")
                if task.status and task.status.message:
                    outputs["response"] += merge_parts(task.status.message.parts)
                if task.artifacts:
                    for artifact in task.artifacts:
                        outputs["response"] += merge_parts(artifact.parts)

            elif payload_type == "status_update":
                update = event.status_update
                # Track latest status
                if update.status and update.status.message:
                    outputs["response"] += merge_parts(update.status.message.parts)

            elif payload_type == "artifact_update":
                update = event.artifact_update
                if update.artifact:
                    outputs["response"] += merge_parts(update.artifact.parts)

        return outputs


async def send_message_with_parts(parts: list, base_url: str, context_id: str | None = None, task_id: str | None = None, streaming=False):
    """Send a message with custom parts. Returns dict with context_id, task_id, response and status (if exists)"""
    async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as httpx_client:
        resolver = A2ACardResolver(httpx_client=httpx_client, base_url=base_url)
        agent_card = await resolver.get_agent_card()
        config = ClientConfig(
            httpx_client=httpx_client,
            streaming=streaming,
        )
        factory = ClientFactory(config)
        client = factory.create(agent_card)

        outbound_msg = create_message_with_parts(parts=parts, context_id=context_id, task_id=task_id)
        request = SendMessageRequest(message=outbound_msg)

        outputs = {
            "response": "",
            "context_id": None,
            "task_id": None,
            "raw_message": None,
        }

        async for event in client.send_message(request):
            payload_type = event.WhichOneof("payload")

            if payload_type == "message":
                msg = event.message
                outputs["context_id"] = msg.context_id or None
                outputs["task_id"] = msg.task_id or None
                outputs["response"] += merge_parts(msg.parts)
                outputs["raw_message"] = msg

            elif payload_type == "task":
                task = event.task
                outputs["context_id"] = task.context_id or None
                outputs["task_id"] = task.id or None
                if task.status and task.status.state:
                    from a2a.types import TaskState
                    state_map = {
                        TaskState.TASK_STATE_COMPLETED: "completed",
                        TaskState.TASK_STATE_FAILED: "failed",
                        TaskState.TASK_STATE_WORKING: "working",
                    }
                    outputs["status"] = state_map.get(task.status.state, "unknown")
                if task.status and task.status.message:
                    outputs["response"] += merge_parts(task.status.message.parts)
                    outputs["raw_message"] = task.status.message
                if task.artifacts:
                    for artifact in task.artifacts:
                        outputs["response"] += merge_parts(artifact.parts)

            elif payload_type == "status_update":
                update = event.status_update
                if update.status and update.status.message:
                    outputs["response"] += merge_parts(update.status.message.parts)

            elif payload_type == "artifact_update":
                update = event.artifact_update
                if update.artifact:
                    outputs["response"] += merge_parts(update.artifact.parts)

        return outputs
