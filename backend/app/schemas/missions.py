from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class MissionRequest(BaseModel):
    target: str = Field(..., example="metasploitable")
    prompt: Optional[str] = Field(
        None,
        description="Optional instructions to guide the agent's strategy.",
        example=(
            "Perform a comprehensive penetration test. "
            "Enumerate all open ports and services, identify vulnerabilities, "
            "attempt exploitation of confirmed weaknesses, "
            "and document all findings with evidence."
        ),
    )


class MissionResponse(BaseModel):
    status: str
    target: str
    data: Any


class ModelUsage(BaseModel):
    """Normalized token/latency counters for one agent, all providers alike."""

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    call_count: int = 0
    total_latency_seconds: float = 0.0


class AgentModelUsage(BaseModel):
    """Which model/provider an agent used, plus its accumulated usage."""

    model: str
    provider: str
    usage: ModelUsage


class MissionMetrics(BaseModel):
    """Aggregated totals across every agent in the mission."""

    total_prompt_tokens: int = 0
    total_completion_tokens: int = 0
    total_tokens: int = 0
    total_llm_calls: int = 0
    total_latency_seconds: float = 0.0
    # Wall-clock from created_at to finished_at (or now, if still running).
    duration_seconds: Optional[float] = None
    duration: Optional[str] = Field(None, description="Duration as hh:mm:ss")


class MissionDetailResponse(BaseModel):
    """Full mission view: record + ports + findings + per-agent usage + totals."""

    mission: Dict[str, Any]
    ports: List[Dict[str, Any]]
    findings: List[Dict[str, Any]]
    models: Dict[str, AgentModelUsage] = Field(default_factory=dict)
    metrics: MissionMetrics = Field(default_factory=MissionMetrics)
