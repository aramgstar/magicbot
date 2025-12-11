# handlers/promocodes_handler.py
#
# Обработка промокодов ChudoMaster.
# Поддерживает:
# - проверку существования кода
# - одноразовое использование
# - скидку –20%
# - запись в БД
# - отображение статуса пользователю

from telebot import types
from services.db import get_conn
from services.billing import get_user_tariff


PROMO_SUCCESS_TEXT = (
    "🎉 Промокод успешно активирован!\n"
    "На твою следующую покупку тарифа действует скидка *20%* ✨"
)

PROMO_ALREADY_USED_TEXT = (
    "Этот промокод уже использован.\n"
    "Он даёт скидку только один раз 🙂"
)

PROMO_INVALID_TEXT = (
    "Такого промокода нет 😔\n"
    "Проверь правильность и попробуй ещё раз."
)


def register_promocode_handlers(bot):

    # ===============================
    # 🔹 Кнопка / команда ввода промокода
    # ===============================
    @bot.message_handler(commands=["promo"])
    def ask_promo(message):
        bot.send_message(
            message.chat.id,
            "🎁 Введи свой промокод:",
        )
        bot.register_next_step_handler(message, apply_promo)

    # ===============================
    # 🔹 Основная логика
    # ===============================
    def apply_promo(message):
        user_id = message.from_user.id
        code = message.text.strip().upper()

        conn = get_conn()
        cur = conn.cursor()

        # Проверка: есть ли такой промокод
        cur.execute("SELECT * FROM promocodes WHERE code=?", (code,))
        promo = cur.fetchone()

        if not promo:
            bot.send_message(message.chat.id, PROMO_INVALID_TEXT)
            return

        # Проверка: использовал ли уже этот промокод?
        cur.execute(
            "SELECT 1 FROM user_promo_usage WHERE user_id=? AND code=?",
            (user_id, code),
        )
        used = cur.fetchone()

        if used:
            bot.send_message(message.chat.id, PROMO_ALREADY_USED_TEXT)
            return

        # Записываем использование
        cur.execute(
            """
            INSERT INTO user_promo_usage (user_id, code, used_at)
            VALUES (?, ?, datetime('now'))
            """,
            (user_id, code),
        )
        conn.commit()
        conn.close()

        bot.send_message(message.chat.id, PROMO_SUCCESS_TEXT)
