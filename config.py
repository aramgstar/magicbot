import os
from dotenv import load_dotenv

load_dotenv()

# ============================
# TELEGRAM
# ============================
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
if not TELEGRAM_TOKEN:
    raise Exception("TELEGRAM_TOKEN отсутствует в .env / Render env")

# Webhook URL (ОБЯЗАТЕЛЬНО для Render)
# Пример: https://magicbot-g98j.onrender.com
TELEGRAM_WEBHOOK_BASE = os.getenv("TELEGRAM_WEBHOOK_BASE", "").rstrip("/")

# Путь вебхука (можно оставить дефолт)
TELEGRAM_WEBHOOK_PATH = os.getenv("TELEGRAM_WEBHOOK_PATH", "/tg/webhook")

# ============================
# OPENAI
# ============================
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# ============================
# NanoBanana
# ============================
NANOBANANA_API_KEY = os.getenv("NANOBANANA_API_KEY")
NANOBANANA_BASE_URL = os.getenv(
    "NANOBANANA_BASE_URL",
    "https://api.nanobananaapi.ai/api/v1/nanobanana",
).rstrip("/")
NANOBANANA_MODEL = os.getenv("NANOBANANA_MODEL", "nano-banana-pro")

# ============================
# Kling (JWT auth)
# ============================
KLING_ACCESS_KEY = os.getenv("KLING_ACCESS_KEY")
KLING_SECRET_KEY = os.getenv("KLING_SECRET_KEY")
KLING_API_BASE_URL = os.getenv("KLING_API_BASE_URL", "https://api.klingai.com").rstrip("/")

# ============================
# Payments
# ============================
PAYMENTS_PROVIDER_TOKEN = os.getenv("PAYMENTS_PROVIDER_TOKEN")
PAYMENTS_CURRENCY = os.getenv("PAYMENTS_CURRENCY", "RUB")