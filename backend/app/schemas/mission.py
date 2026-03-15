from typing import Any, Optional

from pydantic import BaseModel, Field


class MissionRequest(BaseModel):
    target: str = Field(..., example="172.21.0.")
    prompt: Optional[str] = Field(
        None,
        description="Optional instructions to guide the agent's strategy.",
        example=(
            "Perform a comprehensive penetration test."
            "Enumerate all open ports and services, identify vulnerabilities,"
            "attempt exploitation of confirmed weaknesses,"
            "and document all findings with evidence."
        )
    )

class MissionResponse(BaseModel):
    status: str
    target: str
    data: Any
