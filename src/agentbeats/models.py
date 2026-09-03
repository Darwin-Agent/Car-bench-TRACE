from typing import Any
from pydantic import BaseModel, HttpUrl


class EvalRequest(BaseModel):
    agent_under_test: HttpUrl
    config: dict[str, Any]
