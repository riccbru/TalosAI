from pydantic import BaseModel, Field


class MissionRequest(BaseModel):
    target: str = Field(..., example="0.0.0.0", description="The IP or domain to analyze") # noqa: E501

class MissionResponse(BaseModel):
    status: str
    target: str
    data: str
