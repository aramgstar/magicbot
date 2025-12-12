# handlers/payments.py
#
# Тарифы + оплата через Telegram Payments.
# /buy или /pay — показать тарифы.
# Кнопка "👤 Мой тариф и баланс" из меню показывает баланс + эти же кнопки.
# Успешная оплата — начисление токенов + сохранение тарифа + тарифные цены.

from telebot import TeleBot, types
from telebot.types import LabeledPrice

from config import PAYMENTS_PROVIDER_TOKEN, PAYMENTS_CURRENCY
from services.billing import (
    add_tokens,
    format_balance_message,
    set_last_tariff,
    apply_tariff_pricing,
)

# ============================
# 🔹 Тарифы
# ============================

TARIFFS = {
    "start": {
        "title": "START",
        "description": "Базовый доступ к магии ChudoMaster ✨",
        "price_rub": 249,
    },
    "pro": {
        "title": "PRO",
        "description": "Больше магии и экспериментов ✨",
        "price_rub": 499,
    },
    "max": {
        "title": "MAX",
        "description": "Максимальный запас чудес ✨",
        "price_rub": 949,
    },
}

# Сколько токенов даёт каждый тариф
TARIFF_TOKENS = {
    "start": 124,
    "pro": 249,
    "max": 474,
}


def build_tariffs_keyboard() -> types.InlineKeyboardMarkup:
    """
    Клавиатура с кнопками выбора тарифа.
    """
    kb = types.InlineKeyboardMarkup()
    kb.add(
        types.InlineKeyboardButton(
            text=f"START — {TARIFFS['start']['price_rub']} ₽",
            callback_data="buy_start",
        )
    )
    kb.add(
        types.InlineKeyboardButton(
            text=f"PRO — {TARIFFS['pro']['price_rub']} ₽",
            callback_data="buy_pro",
        )
    )
    kb.add(
        types.InlineKeyboardButton(
            text=f"MAX — {TARIFFS['max']['price_rub']} ₽",
            callback_data="buy_max",
        )
    )
    return kb


def tariffs_text() -> str:
    """
    Красивое описание тарифов с упором на токены.
    """
    lines: list[str] = []
    lines.append("📦 *Тарифы:*")
    lines.append("")

    for key in ("start", "pro", "max"):
        t = TARIFFS[key]
        tokens = TARIFF_TOKENS.get(key, 0)
        lines.append(
            f"*{t['title']}* — {t['price_rub']} ₽\n"
            f"• {tokens} токенов для магии ✨\n"
        )

    return "\n".join(lines)


def register_payment_handlers(bot: TeleBot):
    """
    Регистрация всех хендлеров, связанных с оплатой:
    - /buy, /pay — показать тарифы
    - callback buy_start / buy_pro / buy_max
    - pre_checkout_query
    - successful_payment
    """

    # /buy или /pay — показать тарифы + кнопки
    @bot.message_handler(commands=["buy", "pay"])
    def buy_handler(message: types.Message):
        kb = build_tariffs_keyboard()
        bot.send_message(
            message.chat.id,
            tariffs_text(),
            parse_mode="Markdown",
            reply_markup=kb,
        )

    # обработка нажатий на кнопки тарифов
    @bot.callback_query_handler(func=lambda c: c.data and c.data.startswith("buy_"))
    def process_buy_callback(callback: types.CallbackQuery):
        tariff_key = callback.data.split("_", 1)[1]  # "start" / "pro" / "max"
        tariff = TARIFFS.get(tariff_key)

        if not tariff:
            bot.answer_callback_query(
                callback.id,
                "Неизвестный тариф 🤔",
                show_alert=True,
            )
            return

        if not PAYMENTS_PROVIDER_TOKEN:
            bot.answer_callback_query(
                callback.id,
                "Оплата временно недоступна. Попробуй чуть позже 🙏",
                show_alert=True,
            )
            return

        prices = [
            LabeledPrice(
                label=tariff["title"],
                amount=tariff["price_rub"] * 100,  # копейки
            )
        ]

        bot.answer_callback_query(callback.id)

        bot.send_invoice(
            chat_id=callback.message.chat.id,
            title=f"Тариф {tariff['title']}",
            description=tariff["description"],
            provider_token=PAYMENTS_PROVIDER_TOKEN,
            currency=PAYMENTS_CURRENCY,
            prices=prices,
            start_parameter=f"{tariff_key}_sub",
            invoice_payload=tariff_key,  # вернётся в successful_payment
        )

    # pre_checkout_query — обязательно отвечаем ok=True,
    # иначе Telegram не завершит оплату.
    @bot.pre_checkout_query_handler(func=lambda q: True)
    def checkout_process(pre_checkout_query: types.PreCheckoutQuery):
        bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)

    # успешная оплата
    @bot.message_handler(content_types=["successful_payment"])
    def successful_payment_handler(message: types.Message):
        sp = message.successful_payment
        user_id = message.from_user.id
        chat_id = message.chat.id

        tariff_key = sp.invoice_payload  # "start" / "pro" / "max"
        tariff = TARIFFS.get(tariff_key, {})
        title = tariff.get("title", tariff_key.upper())

        total_rub = sp.total_amount / 100.0
        currency = sp.currency

        # Сколько токенов начисляем
        tokens_to_add = TARIFF_TOKENS.get(tariff_key, 0)
        tokens_added = add_tokens(user_id, tokens_to_add)

        # Запоминаем тариф и его тарифные цены
        set_last_tariff(user_id, tariff_key)
        apply_tariff_pricing(user_id, tariff_key)

        balance_text = format_balance_message(user_id)

        bot.send_message(
            chat_id,
            "✅ *Оплата прошла успешно!*\n\n"
            f"Тариф: *{title}*\n"
            f"Сумма: *{total_rub:.2f} {currency}*\n"
            f"Начислено токенов: *{tokens_added}*\n\n"
            f"{balance_text}",
            parse_mode="Markdown",
        )