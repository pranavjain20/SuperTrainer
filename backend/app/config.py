from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql+asyncpg://supertrainer:supertrainer@localhost:5434/supertrainer"
    test_database_url: str = "postgresql+asyncpg://supertrainer_test:supertrainer_test@localhost:5433/supertrainer_test"

    # External APIs (not needed until Week 3+)
    deepgram_api_key: str = ""
    anthropic_api_key: str = ""

    # Supabase (not needed until Week 3+)
    supabase_url: str = ""
    supabase_key: str = ""

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
