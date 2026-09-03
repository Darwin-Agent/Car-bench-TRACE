"""Turn metrics schema for CAR-bench A2A evaluation.

Defines constants and helpers for per-turn metrics communicated from the agent
under test to the evaluator via Message.metadata.
"""

# Metadata key for turn metrics on agent-under-test-to-evaluator final responses
TURN_METRICS_KEY = "turn_metrics"

# Source tags for evaluator-to-agent-under-test messages
SOURCE_KEY = "source"
SOURCE_USER = "user"
SOURCE_ENVIRONMENT = "environment"

# Turn metrics field names
PROMPT_TOKENS = "prompt_tokens"
COMPLETION_TOKENS = "completion_tokens"
COST = "cost"
MODEL = "model"
THINKING_TOKENS = "thinking_tokens"
NUM_LLM_CALLS = "num_llm_calls"
AVG_LLM_CALL_TIME_MS = "avg_llm_call_time_ms"
NUM_PASSES = "num_passes"
QUOTA_WAIT_TIME_MS = "quota_wait_time_ms"


def extract_turn_metrics(metadata) -> dict:
    """Extract turn_metrics from protobuf Struct metadata or dict.

    Returns dict with safe defaults for all fields.
    """
    defaults = {
        PROMPT_TOKENS: 0,
        COMPLETION_TOKENS: 0,
        COST: 0.0,
        MODEL: "",
        THINKING_TOKENS: 0,
        NUM_LLM_CALLS: 0,
        AVG_LLM_CALL_TIME_MS: 0.0,
        NUM_PASSES: 1,
        QUOTA_WAIT_TIME_MS: 0.0,
    }

    if metadata is None:
        return defaults

    # Handle protobuf Struct (has .fields attribute)
    if hasattr(metadata, "fields"):
        fields = metadata.fields
        if TURN_METRICS_KEY not in fields:
            return defaults
        # Extract from Struct's nested struct_value
        metrics_value = fields[TURN_METRICS_KEY]
        if hasattr(metrics_value, "struct_value"):
            metrics_fields = metrics_value.struct_value.fields
            result = {}
            for key, default in defaults.items():
                if key in metrics_fields:
                    val = metrics_fields[key]
                    # Use WhichOneof to determine the actual value type
                    kind = val.WhichOneof("kind") if hasattr(val, "WhichOneof") else None
                    if kind == "number_value":
                        result[key] = val.number_value
                    elif kind == "string_value":
                        result[key] = val.string_value
                    elif kind == "bool_value":
                        result[key] = val.bool_value
                    else:
                        result[key] = default
                else:
                    result[key] = default
            return result

    # Handle dict
    if isinstance(metadata, dict):
        metrics = metadata.get(TURN_METRICS_KEY, {})
        if not metrics:
            return defaults
        return {key: metrics.get(key, default) for key, default in defaults.items()}

    return defaults


def reported_turn_metric_fields(metadata) -> list[str]:
    """Return fields actually supplied by the participant, without defaults."""

    if metadata is None:
        return []
    if hasattr(metadata, "fields"):
        fields = metadata.fields
        if TURN_METRICS_KEY not in fields:
            return []
        metrics_value = fields[TURN_METRICS_KEY]
        if hasattr(metrics_value, "struct_value"):
            return sorted(metrics_value.struct_value.fields)
    if isinstance(metadata, dict):
        metrics = metadata.get(TURN_METRICS_KEY)
        if isinstance(metrics, dict):
            return sorted(metrics)
    return []
