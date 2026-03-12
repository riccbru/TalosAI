from pydantic import BaseModel
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    OLLAMA_BASE_URL: str = "http://ollama:11434"
    DATABASE_URL: str = "postgresql+asyncpg://talos_admin:talos_passwd@db:5432/talos_db"

    class Config:
        env_file = ".env"

class AgentConfig(BaseModel):
    model: str
    system_prompt: str

MODEL_ASSIGNMENT = {
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
        system_prompt="Infiltrator: Analyze services for exploitation vectors and CVEs."
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

settings = Settings()
