from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # PostgreSQL
    postgres_user: str = "newsuser"
    postgres_password: str = "123456789"
    postgres_db: str = "news_hub"
    postgres_host: str = "localhost"
    postgres_port: int = 5432

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    environment: str = "development"
    log_level: str = "info"

    # 管理员
    admin_enabled: bool = True
    admin_password: str = "admin123"

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+psycopg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    model_config = {"env_prefix": ""}


settings = Settings()
