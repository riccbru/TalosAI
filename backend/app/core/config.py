from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://talos_admin:talos_passwd@talos_db:5432/talos_db"
    OLLAMA_BASE_URL: str = "http://ollama:11434"

    class Config:
        env_file = ".env"

settings = Settings()
