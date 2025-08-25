from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv
import os

# Load .env at import time for convenience
load_dotenv(dotenv_path=Path(".") / ".env")


@dataclass
class Settings:
    # Example env vars you'll actually need later
    GOOGLE_PROJECT_ID: str | None = os.getenv("GOOGLE_PROJECT_ID")
    IMAGE_API_KEY: str | None = os.getenv("IMAGE_API_KEY")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    GOOGLE_API_KEY: str | None = os.getenv("GOOGLE_API_KEY")
    LLM_MODEL: str = os.getenv("LLM_MODEL", "models/gemini-2.0-flash-001")


settings = Settings()
