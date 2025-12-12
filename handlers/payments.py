# handlers/payments.py
#
# Оплата через Telegram Payments (ЮKassa).
# Показывает 3 тарифа, по нажатию сразу открывает инвойс (без промокодов).
# Начисляет токены и применяет тарифные цены.
#
# Важно:
# - Использует PAYMENTS_PROVIDER_TOKEN из config.py
# - Вся логика в одном register_payment_handlers(bot)

from telebot import types
from telebot.types import LabeledPrice

from config import PAYMENTS_PROVIDER_TOKEN, PAYMENTS_CURRENCY
from services.billing import add_tokens, set_last_tariff, apply_tariff_pricing, format_balance_message

TARIFFS = {
    "start": {"title": "START", "description": "Базовый доступ к магии ✨", "price_rub": 249},
    "pro":   {"title": "PRO",   "description": "Больше магии и экспериментов ✨", "price_rub": 499},
    "max":   {"title": "MAX",   "description": "Максимальный запас чудес ✨", "price_rub": 949},
}

TARIFF_TOKENS = {
    "start": 124,
    "pro": 249,
    "max": 474,
}


def build_tariffs_keyboard() -> types.InlineKeyboardMarkup:
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton(text=f"START — {TARIFFS['start']['price_rub']} ₽", callback_data="buy:start"))
    kb.add(types.InlineKeyboardButton(text=f"PRO — {TARIFFS['pro']['price_rub']} ₽", callback_data="buy:pro"))
    kb.add(types.InlineKeyboardButton(text=f"MAX — {TARIFFS['max']['price_rub']} ₽", callback_data="buy:max"))
    return kb


def tariffs_text() -> str:
    return (
        "📦 *Тарифы:*\n\n"
        f"*START* — 249 ₽ → *{TARIFF_TOKENS['start']}* токенов\n"
        f"*PRO* — 499 ₽ → *{TARIFF_TOKENS['pro']}* токенов\n"
        f"*MAX* — 949 ₽ → *{TARIFF_TOKENS['max']}* токенов\n"
    )


def register_payment_handlers(bot):

    # /buy /pay — показать тарифы
    @bot.message_handler(commands=["buy", "pay"])
    def cmd_buy(message):
        bot.send_message(
            message.chat.id,
            tariffs_text(),
            parse_mode="Markdown",
            reply_markup=build_tariffs_keyboard(),
        )

    # Нажатие на тариф — сразу открываем оплату
    @bot.callback_query_handler(func=lambda c: c.data and c.data.startswith("buy:"))
    def buy_callback(call):
        tariff_key = call.data.split(":", 1)[1]
        tariff = TARIFFS.get(tariff_key)

        if not tariff:
            bot.answer_callback_query(call.id, "Неизвестный тариф", show_alert=True)
            return

        if not PAYMENTS_PROVIDER_TOKEN:
            bot.answer_callback_query(call.id, "Оплата сейчас недоступна (нет токена провайдера)", show_alert=True)
            return

        bot.answer_callback_query(call.id)

        prices = [LabeledPrice(label=tariff["title"], amount=int(tariff["price_rub"]) * 100)]

        bot.send_invoice(
            chat_id=call.message.chat.id,
            title=f"Тариф {tariff['title']}",
            description=tariff["description"],
            provider_token=PAYMENTS_PROVIDER_TOKEN,
            currency=PAYMENTS_CURRENCY,
            prices=prices,
            start_parameter=f"{tariff_key}_sub",
            invoice_payload=tariff_key,  # вернётся в successful_payment
        )

    # Telegram требует pre_checkout ok=True
    @bot.pre_checkout_query_handler(func=lambda q: True)
    def pre_checkout(pre_checkout_query):
        bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)

    # Успешная оплата
    @bot.message_handler(content_types=["successful_payment"])
    def success_payment(message):
        sp = message.successful_payment
        user_id = message.from_user.id
        chat_id = message.chat.id

        tariff_key = sp.invoice_payload
        tokens_to_add = int(TARIFF_TOKENS.get(tariff_key, 0))

        add_tokens(user_id, tokens_to_add)
        set_last_tariff(user_id, tariff_key)
        apply_tariff_pricing(user_id, tariff_key)

        balance = format_balance_message(user_id)

        bot.send_message(
            chat_id,
            "✅ *Оплата прошла успешно!*\n\n"
            f"Начислено токенов: *{tokens_to_add}*\n\n"
            f"{balance}\n\n"
            "Если хочешь — сразу жми кнопку из меню и делай магию ✨",
            parse_mode="Markdown",
        )