# config.py
#
# Единая точка настроек для бота.
# Поддерживает:
# - Telegram Bot Token
# - Telegram Payments Provider Token (ЮKassa)
# - NanoBanana PRO
# - Kling v2.5-turbo
# - OpenAI (если понадобится)

import os
from dotenv import load_dotenv

# Загружаем .env из корневой директории проекта
load_dotenv()


# ============================================================
# 🔹 Telegram
# ============================================================

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
if not TELEGRAM_TOKEN:
    raise Exception("❌ TELEGRAM_TOKEN отсутствует в .env")


# ============================================================
# 🔹 Telegram Payments (ЮKassa)
# ============================================================

PAYMENTS_PROVIDER_TOKEN = os.getenv("PAYMENTS_PROVIDER_TOKEN")

if not PAYMENTS_PROVIDER_TOKEN:
    raise Exception(
        "❌ PAYMENTS_PROVIDER_TOKEN отсутствует в .env\n"
        "Добавь его: PAYMENTS_PROVIDER_TOKEN=xxx"
    )

PAYMENTS_CURRENCY = "RUB"  # фиксированно рубли


# ============================================================
# 🔹 OpenAI (если используешь)
# ============================================================

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")


# ============================================================
# 🔹 NanoBanana (всегда PRO)
# ============================================================

NANOBANANA_API_KEY = os.getenv("NANOBANANA_API_KEY")
if not NANOBANANA_API_KEY:
    raise Exception("❌ NANOBANANA_API_KEY отсутствует в .env")

NANOBANANA_BASE_URL = os.getenv(
    "NANOBANANA_BASE_URL",
    "https://api.nanobananaapi.ai/api/v1/nanobanana",
)

# всегда PRO
NANOBANANA_MODEL = "nano-banana-pro"


# ============================================================
# 🔹 Kling v2.5 Turbo
# ============================================================

KLING_ACCESS_KEY = os.getenv("KLING_ACCESS_KEY")
KLING_SECRET_KEY = os.getenv("KLING_SECRET_KEY")

if not KLING_ACCESS_KEY or not KLING_SECRET_KEY:
    raise Exception("❌ KLING_ACCESS_KEY или KLING_SECRET_KEY не заданы в .env")

KLING_API_BASE_URL = os.getenv(
    "KLING_API_BASE_URL",
    "https://api.klingai.com",
)

KLING_MODEL = "kling-v2-5-turbo"


# ============================================================
# 🔹 Прочее
# ============================================================

# Фоновый воркер включён/выключен
USE_BACKGROUND_WORKER = os.getenv("USE_BACKGROUND_WORKER", "1") == "1"


print("✅ Config loaded successfully.")
print("🔹 Telegram OK")
print("🔹 Payments OK")
print("🔹 NanoBanana PRO OK")
print("🔹 Kling v2.5 Turbo OK")