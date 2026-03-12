from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    OLLAMA_BASE_URL: str = "http://ollama:11434"
    DATABASE_URL: str = "postgresql+asyncpg://talos_admin:talos_passwd@db:5432/talos_db"

    class Config:
        env_file = ".env"


settings = Settings()
