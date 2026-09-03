"""Centralized logging configuration for CAR-bench A2A components."""
import os
import sys
import json
from loguru import logger


def configure_logger(role: str, context: str = None, serialize: bool = False):
    """Configure loguru logger for structured logging.
    
    Args:
        role: The role identifier (e.g., "agent", "evaluator", "orchestrator")
        context: Optional context identifier (e.g., "eval", "ctx:abc123")
        serialize: If True, output JSON format; if False, use colored format
        
    Returns:
        Configured logger bound with role and context
    
    Logging behavior:
        - INFO level: Clean logs with role/context/message only
        - DEBUG level: Includes all extra structured fields as key=value pairs
        - JSON mode: All fields included at all levels
    """
    logger.remove()  # Remove default handler
    
    if serialize or os.getenv("LOG_FORMAT") == "json":
        # JSON output includes all extra fields automatically.
        logger.add(
            sys.stderr,
            format="{message}",
            level=os.getenv("LOGURU_LEVEL", "INFO"),
            serialize=True,
        )
    else:
        # Colored console output - show extras only at DEBUG level
        def format_with_extras(record):
            """Format log with extras shown only for DEBUG level."""
            # Base format
            time_str = "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green>"
            level_str = "<level>{level: <8}</level>"
            
            if "context" in record["extra"]:
                base = f"{time_str} | {level_str} | <cyan>{{extra[role]}}</cyan> | <cyan>{{extra[context]}}</cyan> | <level>{{message}}</level>"
            else:
                base = f"{time_str} | {level_str} | <cyan>{{extra[role]}}</cyan> | <level>{{message}}</level>"
            
            # Add extra fields for DEBUG level
            if record["level"].name == "DEBUG":
                extra_fields = {k: v for k, v in record["extra"].items() if k not in ("role", "context")}
                if extra_fields:
                    # Format extras safely
                    extras = []
                    for k, v in extra_fields.items():
                        if isinstance(v, str):
                            # Escape curly braces in strings
                            v_safe = v.replace("{", "{{").replace("}", "}}")
                            extras.append(f"{k}={v_safe}")
                        elif isinstance(v, (dict, list)):
                            # Convert to JSON string and escape braces
                            v_str = json.dumps(v)
                            v_safe = v_str.replace("{", "{{").replace("}", "}}")
                            extras.append(f"{k}={v_safe}")
                        else:
                            extras.append(f"{k}={v}")
                    
                    extra_str = " | " + " | ".join(extras)
                    return base + extra_str + "\n"
            
            return base + "\n"
        
        logger.add(
            sys.stderr,
            format=format_with_extras,
            level=os.getenv("LOGURU_LEVEL", "INFO"),
            colorize=True,
        )
    
    if context:
        return logger.bind(role=role, context=context)
    else:
        return logger.bind(role=role)
