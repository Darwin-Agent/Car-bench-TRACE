from agentbeats.client import send_message, send_message_with_parts
from agentbeats.sync_client import send_message_with_parts_sync


class ToolProvider:
    def __init__(self):
        self._context_ids = {}
        self._task_ids = {}

    async def talk_to_agent(self, message: str, url: str, new_conversation: bool = False):
        """
        Communicate with another agent by sending a message and receiving their response.

        Args:
            message: The message to send to the agent
            url: The agent's URL endpoint
            new_conversation: If True, start fresh conversation; if False, continue existing conversation

        Returns:
            str: The agent's response message
        """
        outputs = await send_message(
            message=message,
            base_url=url,
            context_id=None if new_conversation else self._context_ids.get(url, None),
            task_id=None if new_conversation else self._task_ids.get(url, None),
        )
        if outputs.get("status", "completed") != "completed":
            raise RuntimeError(f"{url} responded with: {outputs}")
        self._context_ids[url] = outputs.get("context_id", None)
        self._task_ids[url] = outputs.get("task_id", None)
        return outputs["response"]

    async def talk_to_agent_with_parts(self, parts, url: str, new_conversation: bool = False):
        """
        Communicate with another agent by sending a message with custom parts.

        Args:
            parts: List of Part objects to send
            url: The agent's URL endpoint
            new_conversation: If True, start fresh conversation; if False, continue existing conversation

        Returns:
            Message: The agent's response message object (with parts)
        """
        outputs = await send_message_with_parts(
            parts=parts,
            base_url=url,
            context_id=None if new_conversation else self._context_ids.get(url, None),
            task_id=None if new_conversation else self._task_ids.get(url, None),
        )
        if outputs.get("status", "completed") != "completed":
            raise RuntimeError(f"{url} responded with: {outputs}")
        self._context_ids[url] = outputs.get("context_id", None)
        self._task_ids[url] = outputs.get("task_id", None)
        return outputs["raw_message"]  # Return raw Message object

    def talk_to_agent_with_parts_sync(self, parts, url: str, new_conversation: bool = False, metadata: dict | None = None):
        """
        Communicate with another agent synchronously (safe for use in thread pools).

        Args:
            parts: List of Part objects to send
            url: The agent's URL endpoint
            new_conversation: If True, start fresh conversation; if False, continue existing conversation
            metadata: Optional metadata dict to attach to the outbound message

        Returns:
            Message or Artifact: The agent's response (Message for intermediate turns,
            first Artifact for final answers)
        """
        outputs = send_message_with_parts_sync(
            parts=parts,
            base_url=url,
            context_id=None if new_conversation else self._context_ids.get(url, None),
            task_id=None if new_conversation else self._task_ids.get(url, None),
            metadata=metadata,
        )
        if outputs.get("status", "completed") != "completed":
            raise RuntimeError(f"{url} responded with: {outputs}")
        self._context_ids[url] = outputs.get("context_id", None)
        self._task_ids[url] = outputs.get("task_id", None)
        # Prefer raw_message (intermediate turns), fall back to first artifact (final answers)
        if outputs["raw_message"] is not None:
            return outputs["raw_message"]
        if outputs.get("raw_artifacts"):
            return outputs["raw_artifacts"][0]
        return outputs["raw_message"]

    def reset(self):
        self._context_ids = {}
        self._task_ids = {}
