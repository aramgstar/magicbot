# handlers/profile_handler.py
#
# Простой и понятный профиль для пользователя ChudoMaster.
# Показывает:
# - токены
# - бесплатные изображения
# - тариф
# - статус автопродления
# - кнопки пополнения и рефералов

from telebot import types
from services.billing import (
    format_balance_message,
    get_user_tariff,
)
from services.db import get_auto_renew
from handlers.referrals_handler import _get_referral_stats


AUTO_RENEW_ON = "🔁 Автопродление: Включено"
AUTO_RENEW_OFF = "🔁 Автопродление: Выключено"


def register_profile_handlers(bot):

    # =====================================
    # 👤 Команда /profile
    # =====================================
    @bot.message_handler(commands=["profile"])
    @bot.message_handler(func=lambda m: m.text == "👤 Мой профиль")
    def show_profile(message):
        user_id = message.from_user.id

        reply = "👤 *Твой профиль*\n\n"
        reply += format_balance_message(user_id) + "\n"

        # тариф
        tariff = get_user_tariff(user_id)
        if tariff:
            reply += f"💳 Тариф: *{tariff.upper()}*\n"

        # автопродление
        auto = get_auto_renew(user_id)
        if auto and auto["status"] == 1:
            reply += AUTO_RENEW_ON + "\n"
        else:
            reply += AUTO_RENEW_OFF + "\n"

        # рефералы
        invited, bonus = _get_referral_stats(user_id)
        reply += f"👥 Приглашено друзей: *{invited}*\n"

        # кнопки
        kb = types.InlineKeyboardMarkup()

        kb.add(
            types.InlineKeyboardButton(
                "💳 Пополнить токены",
                callback_data="open_payments"
            )
        )

        kb.add(
            types.InlineKeyboardButton(
                "👥 Пригласить друга",
                url=f"https://t.me/{bot.get_me().username}?start=ref{user_id}"
            )
        )

        kb.add(
            types.InlineKeyboardButton(
                "🔁 Настройки автопродления",
                callback_data="toggle_auto_renew"
            )
        )

        bot.send_message(
            message.chat.id,
            reply,
            parse_mode="Markdown",
            reply_markup=kb
        )

    # =====================================
    # 🔁 Переключение автопродления
    # =====================================
    @bot.callback_query_handler(func=lambda c: c.data == "toggle_auto_renew")
    def toggle_auto_renew(call):
        user_id = call.from_user.id

        auto = get_auto_renew(user_id)
        from services.billing import enable_auto_renew, disable_auto_renew, get_user_tariff

        tariff = get_user_tariff(user_id)
        if not tariff:
            bot.answer_callback_query(
                call.id,
                "У тебя ещё не выбран тариф 🙂",
                show_alert=True
            )
            return

        if not auto or auto["status"] == 0:
            enable_auto_renew(user_id, tariff)
            bot.answer_callback_query(call.id, "Автопродление включено 🔁")
        else:
            disable_auto_renew(user_id)
            bot.answer_callback_query(call.id, "Автопродление отключено ❌")

        # Обновляем профиль
        bot.delete_message(call.message.chat.id, call.message.message_id)
        show_profile(call.message)
