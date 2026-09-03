"""Server entry point for CAR-bench agent under test."""
import argparse
import os
import sys
from pathlib import Path
import warnings

import uvicorn
from starlette.applications import Starlette

# Suppress Pydantic serialization warnings from litellm types
# These occur because litellm's Message/Choices types don't set all optional fields
warnings.filterwarnings(
    "ignore",
    message=".*Pydantic serializer warnings.*",
    category=UserWarning,
    module="pydantic.main"
)

from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.server.routes import create_jsonrpc_routes, create_agent_card_routes
from a2a.types import AgentCard

from car_bench_agent import CARBenchAgentExecutor

sys.path.insert(0, str(Path(__file__).parent.parent))
from logging_utils import configure_logger
sys.path.pop(0)

logger = configure_logger(role="agent_under_test", context="server")


def _env_float(name: str) -> float | None:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return None
    return float(value)


def prepare_agent_card(url: str) -> AgentCard:
    """Create the agent card for the CAR-bench agent under test."""
    card = AgentCard(
        name="car_bench_agent",
        description="In-car voice assistant agent for CAR-bench evaluation",
        version="1.0.0",
        default_input_modes=["text/plain", "application/json"],
        default_output_modes=["text/plain", "application/json"],
    )

    # A2A 1.0 supported interface.
    iface = card.supported_interfaces.add()
    iface.url = url
    iface.protocol_binding = "JSONRPC"
    iface.protocol_version = "1.0"

    # Capabilities — explicitly declare all
    card.capabilities.streaming = False
    card.capabilities.push_notifications = False
    card.capabilities.extended_agent_card = False

    # Skills
    skill = card.skills.add()
    skill.id = "car_assistant"
    skill.name = "In-Car Voice Assistant"
    skill.description = "Helps drivers with navigation, communication, charging, and other in-car tasks"
    skill.tags.extend(["benchmark", "car-bench", "voice-assistant"])

    return card


def main():
    parser = argparse.ArgumentParser(description="Run the CAR-bench agent (agent under test).")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Host to bind the server")
    parser.add_argument("--port", type=int, default=8080, help="Port to bind the server")
    parser.add_argument("--card-url", type=str, help="External URL for the agent card")
    parser.add_argument(
        "--agent-llm",
        type=str,
        default=None,  # Will use env var or fallback
        help="LLM model (can also be set via AGENT_LLM env var)"
    )
    parser.add_argument("--temperature", type=float, default=None, help="Temperature for the LLM")
    parser.add_argument("--thinking", action="store_true", help="Enable thinking mode for the LLM")
    parser.add_argument(
        "--reasoning-effort",
        type=str,
        default=None,
        help="Optional reasoning effort level for the LLM",
    )
    parser.add_argument(
        "--api-mode",
        choices=("chat", "responses"),
        default=None,
        help="OpenAI-compatible API mode (can also be set via AGENT_API_MODE)",
    )
    parser.add_argument(
        "--responses-state-mode",
        choices=("stateless", "provider-default"),
        default=None,
        help=(
            "Responses conversation state mode "
            "(can also be set via AGENT_RESPONSES_STATE_MODE)"
        ),
    )
    parser.add_argument("--interleaved-thinking", action="store_true", help="Enable interleaved thinking for the LLM")
    args = parser.parse_args()

    # Support both command-line args and environment variables
    # Priority: CLI args > env vars > default
    agent_llm = args.agent_llm or os.getenv("AGENT_LLM", "gemini/gemini-2.5-flash")
    api_mode = args.api_mode or os.getenv("AGENT_API_MODE", "responses").strip().lower()
    if api_mode not in {"chat", "responses"}:
        parser.error("AGENT_API_MODE must be 'chat' or 'responses'")
    responses_state_mode = (
        args.responses_state_mode
        or os.getenv("AGENT_RESPONSES_STATE_MODE", "stateless").strip().lower()
    )
    if responses_state_mode not in {"stateless", "provider-default"}:
        parser.error(
            "AGENT_RESPONSES_STATE_MODE must be 'stateless' or 'provider-default'"
        )
    completion_kwargs = {
        "temperature": (
            args.temperature
            if args.temperature is not None
            else _env_float("AGENT_TEMPERATURE")
        ),
        "thinking": args.thinking or (os.getenv("AGENT_THINKING", "false").lower() == "true"),
        "reasoning_effort": args.reasoning_effort or os.getenv("AGENT_REASONING_EFFORT"),
        "interleaved_thinking": args.interleaved_thinking or (os.getenv("AGENT_INTERLEAVED_THINKING", "false").lower() == "true"),
    }

    logger.info(
        "Starting CAR-bench agent",
        model=agent_llm,
        api_mode=api_mode,
        responses_state_mode=responses_state_mode,
        temperature=completion_kwargs["temperature"],
        thinking=completion_kwargs["thinking"],
        reasoning_effort=completion_kwargs["reasoning_effort"],
        interleaved_thinking=completion_kwargs["interleaved_thinking"],
        host=args.host,
        port=args.port
    )

    card = prepare_agent_card(args.card_url or f"http://{args.host}:{args.port}/")

    request_handler = DefaultRequestHandler(
        agent_executor=CARBenchAgentExecutor(
            model=agent_llm,
            temperature=completion_kwargs["temperature"],
            thinking=completion_kwargs["thinking"],
            reasoning_effort=completion_kwargs["reasoning_effort"],
            interleaved_thinking=completion_kwargs["interleaved_thinking"],
            api_mode=api_mode,
            responses_state_mode=responses_state_mode,
        ),
        task_store=InMemoryTaskStore(),
        agent_card=card,
    )

    routes = create_jsonrpc_routes(request_handler, "/", enable_v0_3_compat=True)
    card_routes = create_agent_card_routes(card)

    app = Starlette(routes=routes + card_routes)

    uvicorn.run(
        app,
        host=args.host,
        port=args.port,
        timeout_keep_alive=1000,
    )


if __name__ == "__main__":
    main()
