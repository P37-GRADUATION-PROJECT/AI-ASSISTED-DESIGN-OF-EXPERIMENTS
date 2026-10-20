import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    database_url: str
    llm_enabled: bool


def get_settings() -> Settings:
    return Settings(
        database_url=os.getenv("P37_DATABASE_URL", "sqlite:///./p37.db"),
        llm_enabled=os.getenv("P37_LLM_ENABLED", "false").lower() == "true",
    )
