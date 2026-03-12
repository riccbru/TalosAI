from typing import Dict

from pydantic import BaseModel, Field, field_validator

from app.core.models import AVAILABLE_MODELS


class RoleAssignment(BaseModel):
    model_name: str = Field(..., description="The Ollama model ID")
    system_prompt: str

    @field_validator("model_name")
    @classmethod
    def validate_model_exists(cls, v: str) -> str:
        if v not in AVAILABLE_MODELS:
            raise ValueError(
                f"Model '{v}' not found in Ollama. "
            )
        return v

class AgentRegistry(BaseModel):
    roles: Dict[str, RoleAssignment]
