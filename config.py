import os
from dotenv import load_dotenv

# Load .env file
load_dotenv()

# ==========================
# APP CONFIGURATION
# ==========================

APP_NAME = "AI Market Analytics Pro"

APP_VERSION = "1.0.0"

COMPANY_NAME = "Aadesh Analytics"

DEFAULT_ROLE = "user"

# ==========================
# SECURITY
# ==========================

SECRET_KEY = os.getenv(
    "SECRET_KEY",
    "CHANGE_THIS_SECRET_IN_PRODUCTION"
)

JWT_ALGORITHM = "HS256"

SESSION_TIMEOUT = 3600

# ==========================
# DATABASE
# ==========================

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:///market.db"
)

# ==========================
# EMAIL
# ==========================

SMTP_SERVER = os.getenv("SMTP_SERVER", "")

SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))

SMTP_EMAIL = os.getenv("SMTP_EMAIL", "")

SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")

# ==========================
# ADMIN
# ==========================

ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "")

# ==========================
# API KEYS
# ==========================

TWELVEDATA_API_KEY = os.getenv("TWELVEDATA_API_KEY", "")

ALPHA_VANTAGE_API_KEY = os.getenv("ALPHA_VANTAGE_API_KEY", "")

NEWS_API_KEY = os.getenv("NEWS_API_KEY", "")

# ==========================
# PAYMENT
# ==========================

USDT_WALLET = os.getenv("USDT_WALLET", "")
