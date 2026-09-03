"""Server entry point for CAR-bench evaluator agent."""
import argparse
import asyncio
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

from agentbeats.evaluator_executor import EvaluatorExecutor
from car_bench_paths import CAR_BENCH_DATA_DIR
from car_bench_evaluator import CARBenchEvaluator

sys.path.insert(0, str(Path(__file__).parent.parent))
from logging_utils import configure_logger
sys.path.pop(0)

logger = configure_logger(role="evaluator", context="server")


def car_bench_evaluator_agent_card(name: str, url: str) -> AgentCard:
    """Create the agent card for the CAR-bench evaluator."""
    card = AgentCard(
        name=name,
        description="CAR-bench evaluator - tests agents on in-car voice assistant tasks",
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
    card.capabilities.streaming = True
    card.capabilities.push_notifications = False
    card.capabilities.extended_agent_card = False

    # Skills
    skill = card.skills.add()
    skill.id = "car_bench_evaluation"
    skill.name = "CAR-bench Evaluation"
    skill.description = "Evaluates agents on CAR-bench voice assistant tasks"
    skill.tags.extend(["benchmark", "evaluation", "car-bench"])
    skill.examples.extend([
        '{"agent_under_test": "http://localhost:8080", "config": {"num_tasks": 3}}'
    ])

    return card


async def main():
    parser = argparse.ArgumentParser(description="Run the CAR-bench evaluator agent.")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Host to bind the server")
    parser.add_argument("--port", type=int, default=8081, help="Port to bind the server")
    parser.add_argument("--card-url", type=str, help="External URL for the agent card")
    args = parser.parse_args()

    # Auto-configure CAR_BENCH_DATA_DIR if not set
    if "CAR_BENCH_DATA_DIR" not in os.environ:
        if CAR_BENCH_DATA_DIR.exists():
            os.environ["CAR_BENCH_DATA_DIR"] = str(CAR_BENCH_DATA_DIR)
            logger.info(f"Auto-configured CAR_BENCH_DATA_DIR={CAR_BENCH_DATA_DIR}")
        else:
            logger.warning(
                f"CAR_BENCH_DATA_DIR not set and default path not found: {CAR_BENCH_DATA_DIR}. "
                "Prepare third_party/car-bench from the original CAR-bench project before running evaluations."
            )

    agent_url = args.card_url or f"http://{args.host}:{args.port}/"

    logger.info(
        "Starting CAR-bench evaluator server",
        host=args.host,
        port=args.port,
        url=agent_url
    )

    agent = CARBenchEvaluator()
    executor = EvaluatorExecutor(agent)
    agent_card = car_bench_evaluator_agent_card("CARBenchEvaluator", agent_url)

    request_handler = DefaultRequestHandler(
        agent_executor=executor,
        task_store=InMemoryTaskStore(),
        agent_card=agent_card,
    )

    routes = create_jsonrpc_routes(request_handler, "/", enable_v0_3_compat=True)
    card_routes = create_agent_card_routes(agent_card)

    app = Starlette(routes=routes + card_routes)

    uvicorn_config = uvicorn.Config(app, host=args.host, port=args.port)
    uvicorn_server = uvicorn.Server(uvicorn_config)
    await uvicorn_server.serve()


if __name__ == "__main__":
    asyncio.run(main())
