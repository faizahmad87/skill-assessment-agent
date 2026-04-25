from pydantic_settings import BaseSettings
from pydantic import field_validator
from typing import List

class Settings(BaseSettings):
    groq_api_key: str
    database_url: str = "sqlite:///./skill_assessment.db"
    cors_origins: str = "http://localhost:3000"
    groq_model: str = "llama-3.3-70b-versatile"

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    class Config:
        env_file = ".env"

settings = Settings()
