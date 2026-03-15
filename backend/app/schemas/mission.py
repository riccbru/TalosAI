from typing import Any, Optional

from pydantic import BaseModel, Field


class MissionRequest(BaseModel):
    target: str = Field(..., example="192.168.1.1")
    prompt: Optional[str] = Field(
        None,
        example="""Focus on finding exposed database ports
        and skip web directory fuzzing.""",
        description="Optional instructions to guide the agent's strategy."
    )

class MissionResponse(BaseModel):
    status: str
    target: str
    data: Any
