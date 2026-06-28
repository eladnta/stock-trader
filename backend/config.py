from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://stocktrader:changeme@localhost:5432/stocktrader"

    class Config:
        env_file = ".env"

settings = Settings()
