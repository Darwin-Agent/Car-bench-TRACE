import asyncio
from abc import abstractmethod
from pydantic import ValidationError

from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.tasks import TaskUpdater
from a2a.types import (
    Task,
    TaskState,
)
from a2a.helpers.proto_helpers import (
    new_text_message,
    new_task_from_user_message,
)
from a2a.utils.errors import (
    InternalError,
    InvalidParamsError,
    TaskNotCancelableError,
)

from agentbeats.models import EvalRequest


class EvaluatorAgent:

    @abstractmethod
    async def run_eval(self, request: EvalRequest, updater: TaskUpdater) -> None:
        pass

    @abstractmethod
    def validate_request(self, request: EvalRequest) -> tuple[bool, str]:
        pass


class EvaluatorExecutor(AgentExecutor):

    def __init__(self, evaluator_agent: EvaluatorAgent):
        self.agent = evaluator_agent
        self._active_tasks: dict[str, asyncio.Event] = {}  # task_id → cancel event
        self._task_updaters: dict[str, TaskUpdater] = {}

    async def execute(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        request_text = context.get_user_input()
        try:
            req: EvalRequest = EvalRequest.model_validate_json(request_text)
            ok, msg = self.agent.validate_request(req)
            if not ok:
                raise InvalidParamsError(message=msg)
        except ValidationError as e:
            raise InvalidParamsError(message=e.json())

        msg = context.message
        if msg:
            task = new_task_from_user_message(msg)
            await event_queue.enqueue_event(task)
        else:
            raise InvalidParamsError(message="Missing message.")

        updater = TaskUpdater(event_queue, task.id, task.context_id)
        cancel_event = asyncio.Event()
        self._active_tasks[task.id] = cancel_event
        self._task_updaters[task.id] = updater

        await updater.update_status(
            TaskState.TASK_STATE_WORKING,
            new_text_message(f"Starting assessment.\n{req.model_dump_json()}", context_id=context.context_id)
        )

        try:
            await self.agent.run_eval(req, updater)
            if cancel_event.is_set():
                await updater.cancel(new_text_message("Task was canceled.", context_id=context.context_id))
            else:
                await updater.complete()
        except Exception as e:
            if cancel_event.is_set():
                await updater.cancel(new_text_message("Task was canceled.", context_id=context.context_id))
            else:
                print(f"Agent error: {e}")
                await updater.failed(new_text_message(f"Agent error: {e}", context_id=context.context_id))
                raise InternalError(message=str(e))
        finally:
            self._active_tasks.pop(task.id, None)
            self._task_updaters.pop(task.id, None)

    async def cancel(
        self, context: RequestContext, event_queue: EventQueue
    ) -> None:
        task_id = context.task_id
        if task_id and task_id in self._active_tasks:
            # Signal the running task to cancel
            self._active_tasks[task_id].set()
            # Emit canceled status immediately
            if task_id in self._task_updaters:
                updater = self._task_updaters[task_id]
                await updater.cancel(
                    new_text_message("Task canceled by client request.", context_id=context.context_id)
                )
        else:
            raise TaskNotCancelableError(
                message=f"Task {task_id} is not active or not found."
            )
