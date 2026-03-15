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
            system_prompt="Architect: Create a high-level pentest plan. Focus on OODA loops." # noqa: E501
        ),
        "scanner": AgentConfig(
            model="Lily-Cybersecurity-7B:latest",
            system_prompt="Scout: Generate precise Nmap/FFUF commands. No conversational filler." # noqa: E501
        ),
        "tester": AgentConfig(
            model="White-Rabbit-Neo-13B:latest",
            system_prompt="Exploitation Operator: You must use available tools to execute exploits. Do not just describe them; prove them in the terminal." # noqa: E501
        ),
        "critic": AgentConfig(
            model="Foundation-Sec-8B:latest",
            system_prompt="Validator: Review CLI commands for syntax errors and safety."
        ),
        "reporter": AgentConfig(
            model="mistral-nemo:12b",
            system_prompt="Chronicler: Convert raw technical data into structured JSON/PDF prose." # noqa: E501
        )
    }

    model_config = SettingsConfigDict(
        extra="ignore",
        env_file=".env",
        env_file_encoding="utf-8"
    )

settings = Settings()
