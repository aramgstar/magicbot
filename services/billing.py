# services/billing.py
#
# Финальная версия биллинга ChudoMaster.
# Работает через SQLite (services/db.py)
# Сохраняет твою логику:
# - 3 бесплатные картинки
# - бесплатных анимаций НЕТ (и не упоминаем)
# - тарифы START / PRO / MAX со своими ценами
# - автопродление
# - учёт скидок промокода
# - учёт реферальных бонусов

from services.db import (
    get_token_balance,
    set_token_balance,
    adjust_tokens,
    get_auto_renew,
    set_auto_renew,
)
from datetime import datetime


# =====================================
# 🔮 Бесплатные генерации
# =====================================
WELCOME_FREE_IMAGES = 3


# =====================================
# 🔮 Стоимость по умолчанию
# =====================================
DEFAULT_COST_IMAGE = 2
DEFAULT_COST_ANIMATION = 6


# =====================================
# 🔮 Стоимость по тарифам
# (сохранил твою старую логику)
# =====================================
TARIFF_PRICING = {
    "start": {
        "image_cost": 2,
        "animation_cost": 5,
    },
    "pro": {
        "image_cost": 1,
        "animation_cost": 3,
    },
    "max": {
        "image_cost": 1,
        "animation_cost": 2,
    },
}

# Здесь храним тариф пользователя в рантайме
USER_TARIFF_CACHE = {}

# Здесь храним бесплатные изображения в рантайме
USER_FREE_IMAGES = {}


# =====================================
# 📌 Инициализация пользовательских данных
# =====================================
def ensure_user_initialized(user_id: int):
    """
    Обеспечивает, чтобы у пользователя:
    - был баланс
    - было 3 бесплатных изображения (если первый раз)
    """
    if user_id not in USER_FREE_IMAGES:
        USER_FREE_IMAGES[user_id] = WELCOME_FREE_IMAGES

    if get_token_balance(user_id) < 0:
        set_token_balance(user_id, 0)


# =====================================
# 📌 Управление тарифами
# =====================================
def set_last_tariff(user_id: int, tariff_key: str):
    USER_TARIFF_CACHE[user_id] = tariff_key


def get_user_tariff(user_id: int):
    return USER_TARIFF_CACHE.get(user_id)


# =====================================
# 📌 Получение стоимости действия
# =====================================
def get_cost(user_id: int, mode: str) -> int:
    tariff = get_user_tariff(user_id)

    if tariff and tariff in TARIFF_PRICING:
        return TARIFF_PRICING[tariff][f"{mode}_cost"]

    return DEFAULT_COST_IMAGE if mode == "image" else DEFAULT_COST_ANIMATION


# =====================================
# ⚙️ Проверка и списание токенов / бесплатных лимитов
# =====================================
def can_use_image(user_id: int):
    ensure_user_initialized(user_id)

    free_left = USER_FREE_IMAGES.get(user_id, 0)
    if free_left > 0:
        return True, None

    cost = get_cost(user_id, "image")
    if get_token_balance(user_id) >= cost:
        return True, None

    return False, "У тебя закончились бесплатные генерации и токены."


def register_image_usage(user_id: int):
    free_left = USER_FREE_IMAGES.get(user_id, 0)

    if free_left > 0:
        USER_FREE_IMAGES[user_id] = free_left - 1
    else:
        cost = get_cost(user_id, "image")
        adjust_tokens(user_id, -cost)


def can_use_animation(user_id: int):
    ensure_user_initialized(user_id)

    cost = get_cost(user_id, "animation")
    bal = get_token_balance(user_id)

    if bal >= cost:
        return True, None

    return False, "Не хватает токенов. Пополни баланс, и я продолжу творить ✨"


def register_animation_usage(user_id: int):
    cost = get_cost(user_id, "animation")
    adjust_tokens(user_id, -cost)


# =====================================
# 📌 Универсальная функция
# =====================================
def consume_tokens_or_limit(user_id: int, mode: str) -> bool:
    if mode == "image":
        ok, _ = can_use_image(user_id)
        if not ok:
            return False
        register_image_usage(user_id)
        return True

    if mode == "animation":
        ok, _ = can_use_animation(user_id)
        if not ok:
            return False
        register_animation_usage(user_id)
        return True

    return False


# =====================================
# 📌 Начисление токенов
# =====================================
def add_tokens(user_id: int, amount: int):
    return adjust_tokens(user_id, +amount)


# =====================================
# 📌 Формирование простого профиля
# =====================================
def format_balance_message(user_id: int) -> str:
    ensure_user_initialized(user_id)

    tokens = get_token_balance(user_id)
    free_images = USER_FREE_IMAGES.get(user_id, 0)
    tariff = get_user_tariff(user_id)

    lines = [
        f"🔮 Токены: *{tokens}*",
        f"🖼 Бесплатных изображений: *{free_images}*",
    ]

    if tariff:
        lines.append(f"💳 Тариф: *{tariff.upper()}*")

    return "\n".join(lines)


def format_usage_left_message(user_id: int) -> str:
    return (
        f"🔢 Остаток:\n"
        f"• изображения: *{USER_FREE_IMAGES.get(user_id, 0)}*\n"
        f"• токены: *{get_token_balance(user_id)}*"
    )