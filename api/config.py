from pydantic import BaseSettings
from typing import List


class Settings(BaseSettings):
    firebase_project_id: str
    firebase_api_key: str
    gemini_api_key: str
    gemini_model: str = "models/gemini-2.5-flash-lite"
    cors_allow_origins: List[str] = ["*"]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
