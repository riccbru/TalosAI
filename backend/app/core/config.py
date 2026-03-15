from typing import ClassVar, Dict

from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict


class AgentConfig(BaseModel):
    model: str
    system_prompt: str
class Settings(BaseSettings):
    OLLAMA_BASE_URL: str
    DATABASE_URL: str

    MODEL_ASSIGNMENT: ClassVar[Dict[str, AgentConfig]] = {
        "planner": AgentConfig(
            model="deepseek-r1:14b",
            system_prompt=(
                "Strategic Planner: Create a technical audit strategy for the specified target." # noqa: E501
                "Focus on logical phases: Recon -> Enumeration -> Validation."
            )
        ),
        "scanner": AgentConfig(
            model="Lily-Cybersecurity-7B:latest",
            system_prompt=(
                "Technical Scout: You generate and execute CLI commands."
                "Use only tool output. Never invent data or IP addresses."
            )
        ),
        "tester": AgentConfig(
            model="White-Rabbit-Neo-13B:latest",
            system_prompt=(
                "Exploitation Operator: Your goal is to prove vulnerabilities."
                "If a tool returns no results, report 'no evidence found'."
                "Never use placeholders (like 'exploit_name')."
            )
        ),
        "critic": AgentConfig(
            model="Foundation-Sec-8B:latest",
            system_prompt=(
                "Data Auditor: Compare agent claims against raw tool logs."
                "If an agent mentions a service or IP not found"
                "in the logs, flag it as a hallucination."
            )
        ),
        "reporter": AgentConfig(
            model="mistral-nemo:12b",
            system_prompt=(
                "JSON Reporter: Convert validated logs into JSON."
                "If the logs are missing technical data, reflect that accurately."
            )
        )
    }

    model_config = SettingsConfigDict(
        extra="ignore",
        env_file=".env",
        env_file_encoding="utf-8"
    )

settings = Settings()
