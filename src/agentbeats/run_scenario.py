import argparse
import asyncio
import os, sys, time, subprocess, shlex, signal
from pathlib import Path
import tomllib
from typing import Any
import httpx
from dotenv import load_dotenv

from a2a.client import A2ACardResolver

sys.path.insert(0, str(Path(__file__).parent.parent))
from logging_utils import configure_logger
sys.path.pop(0)


# Load .env for local development only (doesn't override existing env vars from GitHub Actions)
load_dotenv(override=False)
logger = configure_logger(role="orchestrator")
DEFAULT_AGENT_STARTUP_TIMEOUT_SECONDS = 90


async def wait_for_agents(
    cfg: dict,
    timeout: int = DEFAULT_AGENT_STARTUP_TIMEOUT_SECONDS,
    evaluate_only: bool = False,
    processes: list[dict[str, Any]] | None = None,
) -> bool:
    """Wait for all agents to be healthy and responding."""
    endpoints = []

    # In evaluate-only mode, only check the evaluator endpoint.
    if evaluate_only:
        endpoints.append(f"http://{cfg['evaluator']['host']}:{cfg['evaluator']['port']}")
    else:
        endpoints.append(f"http://{cfg['agent_under_test']['host']}:{cfg['agent_under_test']['port']}")
        endpoints.append(f"http://{cfg['evaluator']['host']}:{cfg['evaluator']['port']}")

    if not endpoints:
        return True  # No agents to wait for

    logger.info(f"Waiting for {len(endpoints)} agent(s) to be ready", num_agents=len(endpoints))
    start_time = time.time()
    last_errors: dict[str, str] = {}

    async def check_endpoint(endpoint: str) -> bool:
        """Check if an endpoint is responding by fetching the agent card."""
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                resolver = A2ACardResolver(httpx_client=client, base_url=endpoint)
                await resolver.get_agent_card()
                last_errors.pop(endpoint, None)
                return True
        except Exception as e:
            error = f"{type(e).__name__}: {e}"
            last_errors[endpoint] = error
            logger.debug("Agent readiness check failed", endpoint=endpoint, error=error)
            return False

    def exited_processes() -> list[dict[str, Any]]:
        exited = []
        for process_info in processes or []:
            proc = process_info["process"]
            exit_code = proc.poll()
            if exit_code is not None:
                exited.append(
                    {
                        "role": process_info["role"],
                        "endpoint": process_info["endpoint"],
                        "exit_code": exit_code,
                        "cmd": process_info["cmd"],
                    }
                )
        return exited

    while time.time() - start_time < timeout:
        exited = exited_processes()
        if exited:
            logger.error(
                "Agent process exited before readiness",
                exited_processes=exited,
                last_errors=last_errors,
            )
            return False

        ready_status = {}
        for endpoint in endpoints:
            is_ready = await check_endpoint(endpoint)
            ready_status[endpoint] = is_ready
        
        ready_count = sum(ready_status.values())

        if ready_count == len(endpoints):
            logger.info("All agents ready", num_agents=len(endpoints))
            return True

        # Log status for agents that aren't ready yet
        for endpoint, is_ready in ready_status.items():
            if not is_ready:
                logger.debug(
                    "Agent not ready yet",
                    endpoint=endpoint,
                    last_error=last_errors.get(endpoint),
                )
        
        await asyncio.sleep(1)

    logger.error(
        "Timeout waiting for agents",
        ready=ready_count,
        total=len(endpoints),
        timeout=timeout,
        last_errors=last_errors,
    )
    return False


def parse_toml(scenario_path: str) -> dict:
    path = Path(scenario_path)
    if not path.exists():
        logger.error("Scenario file not found", path=str(path))
        sys.exit(1)

    data = tomllib.loads(path.read_text())
    logger.debug("Loaded scenario file", path=str(path))

    def host_port(ep: str):
        s = (ep or "")
        s = s.replace("http://", "").replace("https://", "")
        s = s.split("/", 1)[0]
        host, port = s.split(":", 1)
        return host, int(port)

    if "green_agent" in data or "participants" in data:
        logger.error("Old scenario shape is unsupported; use [evaluator] and [agent_under_test].")
        sys.exit(1)

    evaluator = data.get("evaluator", {})
    agent_under_test = data.get("agent_under_test", {})
    evaluator_host, evaluator_port = host_port(evaluator.get("endpoint", ""))
    aut_host, aut_port = host_port(agent_under_test.get("endpoint", ""))

    cfg = data.get("config", {})
    return {
        "evaluator": {"host": evaluator_host, "port": evaluator_port, "cmd": evaluator.get("cmd", "")},
        "agent_under_test": {"host": aut_host, "port": aut_port, "cmd": agent_under_test.get("cmd", "")},
        "config": cfg,
    }


def main():
    parser = argparse.ArgumentParser(description="Run agent scenario")
    parser.add_argument("scenario", help="Path to scenario TOML file")
    parser.add_argument("--show-logs", action="store_true",
                        help="Show agent stdout/stderr")
    parser.add_argument("--serve-only", action="store_true",
                        help="Start agent servers only without running evaluation")
    parser.add_argument("--evaluate-only", action="store_true",
                        help="Run evaluation only without starting agent servers")
    parser.add_argument(
        "--timeout",
        type=int,
        default=DEFAULT_AGENT_STARTUP_TIMEOUT_SECONDS,
        help=(
            "Timeout in seconds to wait for agents to be ready "
            f"(default: {DEFAULT_AGENT_STARTUP_TIMEOUT_SECONDS})"
        ),
    )
    parser.add_argument("--output", type=str, default="output",
                        help="Output JSON file or directory for timestamped results (default: output)")
    args = parser.parse_args()

    # Validate that --serve-only and --evaluate-only are not both set
    if args.serve_only and args.evaluate_only:
        logger.error("Cannot use both --serve-only and --evaluate-only flags")
        sys.exit(1)

    cfg = parse_toml(args.scenario)

    sink = None if args.show_logs or args.serve_only else subprocess.DEVNULL
    parent_bin = str(Path(sys.executable).parent)
    base_env = os.environ.copy()
    base_env["PATH"] = parent_bin + os.pathsep + base_env.get("PATH", "")

    procs = []
    process_infos = []
    try:
        # Start the agent under test (skip if --evaluate-only).
        if not args.evaluate_only:
            aut = cfg["agent_under_test"]
            cmd_args = shlex.split(aut.get("cmd", ""))
            if cmd_args:
                logger.info(
                    "Starting agent under test",
                    host=aut['host'],
                    port=aut['port']
                )
                proc = subprocess.Popen(
                    cmd_args,
                    env=base_env,
                    stdout=sink, stderr=sink,
                    text=True,
                    start_new_session=True,
                )
                procs.append(proc)
                process_infos.append(
                    {
                        "role": "agent_under_test",
                        "endpoint": f"http://{aut['host']}:{aut['port']}",
                        "cmd": cmd_args,
                        "process": proc,
                    }
                )

        # Start the evaluator (skip if --evaluate-only).
        if not args.evaluate_only:
            evaluator_cmd_args = shlex.split(cfg["evaluator"].get("cmd", ""))
            if evaluator_cmd_args:
                logger.info(
                    "Starting evaluator",
                    host=cfg['evaluator']['host'],
                    port=cfg['evaluator']['port']
                )
                proc = subprocess.Popen(
                    evaluator_cmd_args,
                    env=base_env,
                    stdout=sink, stderr=sink,
                    text=True,
                    start_new_session=True,
                )
                procs.append(proc)
                process_infos.append(
                    {
                        "role": "evaluator",
                        "endpoint": (
                            f"http://{cfg['evaluator']['host']}:"
                            f"{cfg['evaluator']['port']}"
                        ),
                        "cmd": evaluator_cmd_args,
                        "process": proc,
                    }
                )

        # Wait for all agents to be ready
        if not asyncio.run(
            wait_for_agents(
                cfg,
                timeout=args.timeout,
                evaluate_only=args.evaluate_only,
                processes=process_infos,
            )
        ):
            logger.error("Not all agents became ready, exiting")
            return

        logger.info("Agents started successfully", mode="serve" if args.serve_only else "evaluate")
        if args.serve_only:
            while True:
                for proc in procs:
                    if proc.poll() is not None:
                        logger.warning("Agent exited", exit_code=proc.returncode)
                        break
                    time.sleep(0.5)
        else:
            logger.info("Starting evaluation client", output=args.output)
            client_proc = subprocess.Popen(
                [sys.executable, "-m", "agentbeats.client_cli", args.scenario, args.output],
                env=base_env,
                start_new_session=True,
            )
            procs.append(client_proc)
            client_proc.wait()
            if client_proc.returncode:
                logger.error("Evaluation client failed", exit_code=client_proc.returncode)
                sys.exit(client_proc.returncode)

    except KeyboardInterrupt:
        logger.info("Received interrupt signal")

    finally:
        logger.info("Shutting down agents")
        for p in procs:
            if p.poll() is None:
                try:
                    os.killpg(p.pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
        time.sleep(1)
        for p in procs:
            if p.poll() is None:
                try:
                    os.killpg(p.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass


if __name__ == "__main__":
    main()
