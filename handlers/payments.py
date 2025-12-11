# handlers/payments.py
#
# Покупка тарифов через Telegram Payments.
# Простой флоу:
#   1) Юзер выбирает тариф START / PRO / MAX
#   2) Сразу получает счёт внутри Telegram
#   3) После успешной оплаты — начисляем токены и сохраняем тариф

from telebot import types
from telebot.types import LabeledPrice
from datetime import datetime

from config import PAYMENTS_PROVIDER_TOKEN
from services.db import get_conn
from services.billing import (
    add_tokens,
    format_balance_message,
    set_last_tariff,
)

# ============================================================
# 🎁 НАСТРОЙКИ ТАРИФОВ
# ============================================================

TARIFFS = {
    "start": {"title": "START", "price": 249, "tokens": 124},
    "pro":   {"title": "PRO",   "price": 499, "tokens": 249},
    "max":   {"title": "MAX",   "price": 949, "tokens": 474},
}


# ============================================================
# 📌 Регистрация хендлеров
# ============================================================

def register_payment_handlers(bot):

    # /buy или /pay — показать тарифы
    @bot.message_handler(commands=["buy", "pay"])
    def cmd_buy(message):
        kb = types.InlineKeyboardMarkup()
        kb.add(
            types.InlineKeyboardButton(
                "START — 249 ₽", callback_data="tariff_start"
            )
        )
        kb.add(
            types.InlineKeyboardButton(
                "PRO — 499 ₽", callback_data="tariff_pro"
            )
        )
        kb.add(
            types.InlineKeyboardButton(
                "MAX — 949 ₽", callback_data="tariff_max"
            )
        )

        bot.send_message(
            message.chat.id,
            "📦 Выбери тариф, который хочешь активировать:",
            reply_markup=kb,
        )

    # обработка нажатий на кнопки тарифов
    @bot.callback_query_handler(func=lambda c: c.data and c.data.startswith("tariff_"))
    def select_tariff(call: types.CallbackQuery):
        tariff_key = call.data.split("_", 1)[1]  # start / pro / max
        if tariff_key not in TARIFFS:
            bot.answer_callback_query(call.id, "Неизвестный тариф", show_alert=True)
            return

        tariff = TARIFFS[tariff_key]
        bot.answer_callback_query(call.id)

        # сразу создаём счёт без вопросов про промокод
        prices = [
            LabeledPrice(
                label=tariff["title"],
                amount=tariff["price"] * 100,  # в копейках
            )
        ]

        bot.send_invoice(
            chat_id=call.message.chat.id,
            title=f"Тариф {tariff['title']}",
            description=f"Доступ к магии ChudoMaster ✨",
            provider_token=PAYMENTS_PROVIDER_TOKEN,
            currency="RUB",
            prices=prices,
            start_parameter="chudomaster_sub",
            invoice_payload=tariff_key,  # просто ключ тарифа
        )


def register_precheckout(bot):

    @bot.pre_checkout_query_handler(func=lambda q: True)
    def checkout_handler(pre: types.PreCheckoutQuery):
        # здесь можно добавить свои проверки перед оплатой
        bot.answer_pre_checkout_query(pre.id, ok=True)


def register_successful_payment(bot):

    @bot.message_handler(content_types=["successful_payment"])
    def successful_payment(message: types.Message):
        user_id = message.from_user.id
        tariff_key = message.successful_payment.invoice_payload

        tariff = TARIFFS.get(tariff_key)
        if not tariff:
            bot.send_message(
                message.chat.id,
                "Что-то пошло не так при обработке тарифа 🤔",
            )
            return

        amount_rub = message.successful_payment.total_amount / 100
        tokens = tariff["tokens"]

        # 1) начисляем токены
        add_tokens(user_id, tokens)

        # 2) привязываем тариф (в старом billing это просто поле last_tariff)
        set_last_tariff(user_id, tariff_key)

        # 3) пишем покупку в БД (если таблица purchases есть)
        try:
            conn = get_conn()
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO purchases (user_id, tariff_key, amount_rub, tokens_added, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    tariff_key,
                    amount_rub,
                    tokens,
                    datetime.utcnow().isoformat(),
                ),
            )
            conn.commit()
            conn.close()
        except Exception:
            # если таблицы нет — просто не падаем
            pass

        # 4) отвечаем пользователю
        text = (
            "🎉 *Оплата прошла успешно!*\n\n"
            f"Тариф: *{tariff['title']}*\n"
            f"Начислено токенов: *{tokens}*\n"
            f"Сумма: {amount_rub:.2f} ₽\n\n"
            f"{format_balance_message(user_id)}"
        )

        bot.send_message(message.chat.id, text, parse_mode="Markdown")