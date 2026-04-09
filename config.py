import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-in-prod")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Mail (Flask-Mail / dunning emails)
    MAIL_SERVER = os.environ.get("MAIL_SERVER", "smtp.gmail.com")
    MAIL_PORT = int(os.environ.get("MAIL_PORT", 587))
    MAIL_USE_TLS = True
    MAIL_USERNAME = os.environ.get("MAIL_USERNAME")
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD")
    MAIL_DEFAULT_SENDER = os.environ.get("MAIL_DEFAULT_SENDER", "ar@company.com")

    # Stripe payment gateway
    STRIPE_PUBLIC_KEY = os.environ.get("STRIPE_PUBLIC_KEY", "")
    STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY", "")
    STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "")

    # AR business rules
    PAYMENT_TOLERANCE_PCT = float(os.environ.get("PAYMENT_TOLERANCE_PCT", "0.01"))  # 1%
    DEFAULT_CREDIT_LIMIT = float(os.environ.get("DEFAULT_CREDIT_LIMIT", "10000.00"))
    LATE_FEE_RATE = float(os.environ.get("LATE_FEE_RATE", "0.015"))   # 1.5% / month
    DUNNING_GRACE_DAYS = int(os.environ.get("DUNNING_GRACE_DAYS", "3"))

    # Company branding (FR-AR-003)
    COMPANY_NAME = os.environ.get("COMPANY_NAME", "Lincoln Financial Group")
    COMPANY_LOGO_URL = os.environ.get("COMPANY_LOGO_URL", "https://lfg.com/logo.png")
    COMPANY_ADDRESS = os.environ.get("COMPANY_ADDRESS", "150 N. Radnor Chester Rd, Radnor, PA 19087")
    COMPANY_TAX_ID = os.environ.get("COMPANY_TAX_ID", "")

    # ERP integration
    ERP_API_URL = os.environ.get("ERP_API_URL", "")
    ERP_API_KEY = os.environ.get("ERP_API_KEY", "")


class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        "postgresql://postgres:wangu@localhost:5433/accounts_receivable"
    )


class ProductionConfig(Config):
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL")
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"


config = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}
