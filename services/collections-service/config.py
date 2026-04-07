from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql://aruser:arpassword@postgres:5432/accounts_receivable"
    jwt_secret_key: str = "your-super-secret-jwt-key-change-in-production"
    jwt_algorithm: str = "HS256"
    service_name: str = "collections-service"
    auth_service_url: str = "http://auth-service:8001"
    invoice_service_url: str = "http://invoice-service:8002"
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""

    class Config:
        env_file = ".env"


settings = Settings()
