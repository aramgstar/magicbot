# handlers/referrals_handler.py
#
# Реферальная система ChudoMaster:
# - генерация реферальной ссылки
# - сохранение рефералов
# - начисление токенов (+10)
# - отображение статистики

from telebot import types
from services.db import get_conn
from services.billing import add_tokens


REFERRAL_BONUS = 10  # и пригласившему, и приглашенному


def register_referral_handlers(bot):

    # ================================================
    # 🔹 Обработка команды /start с параметром ?start=ref123
    # ================================================
    @bot.message_handler(commands=["start"])
    def start_handler(message):
        user_id = message.from_user.id

        # Если у сообщения есть параметр реферала:
        if "ref" in message.text:
            try:
                ref_id = int(message.text.split("ref")[1])
            except:
                ref_id = None

            if ref_id and ref_id != user_id:
                _process_referral(user_id, ref_id)

        bot.send_message(
            message.chat.id,
            "✨ Добро пожаловать в ChudoMaster!\nТы можешь создавать магию прямо сейчас.",
        )

    # ================================================
    # 🔹 Кнопка/команда /ref для просмотра статистики
    # ================================================
    @bot.message_handler(commands=["ref"])
    def referral_info(message):
        user_id = message.from_user.id
        invited, total_bonus = _get_referral_stats(user_id)

        kb = types.InlineKeyboardMarkup()
        kb.add(
            types.InlineKeyboardButton(
                "🔗 Пригласить друга",
                url=f"https://t.me/{bot.get_me().username}?start=ref{user_id}"
            )
        )

        bot.send_message(
            message.chat.id,
            f"👥 Твои приглашённые: *{invited}*\n"
            f"🎁 Получено бонусов: *{total_bonus} токенов*\n\n"
            "Приглашай друзей и получай магические бонусы ✨",
            parse_mode="Markdown",
            reply_markup=kb
        )


# =====================================================
# 🔧 Внутренние функции
# =====================================================

def _process_referral(invited_id: int, referrer_id: int):
    """
    Обрабатываем факт перехода по реферальной ссылке:
    - записываем в БД
    - выдаём токены обоим
    """
    conn = get_conn()
    cur = conn.cursor()

    # Проверяем — не записан ли уже этот пользователь
    cur.execute("SELECT 1 FROM referrals WHERE invited_id=?", (invited_id,))
    exists = cur.fetchone()

    if exists:
        conn.close()
        return  # уже был реферал, ничего не делаем

    # Добавляем запись
    cur.execute(
        """
        INSERT INTO referrals (referrer_id, invited_id, reward_referrer, reward_invited, created_at)
        VALUES (?, ?, ?, ?, datetime('now'))
        """,
        (referrer_id, invited_id, REFERRAL_BONUS, REFERRAL_BONUS)
    )
    conn.commit()

    # Начисляем токены
    add_tokens(referrer_id, REFERRAL_BONUS)
    add_tokens(invited_id, REFERRAL_BONUS)

    conn.close()


def _get_referral_stats(user_id: int):
    """
    Возвращает:
    - количество приглашённых
    - суммарное количество бонусных токенов
    """
    conn = get_conn()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT COUNT(*), SUM(reward_referrer)
        FROM referrals
        WHERE referrer_id=?
        """,
        (user_id,)
    )

    row = cur.fetchone()
    conn.close()

    invited_count = row[0] or 0
    bonus_sum = row[1] or 0

    return invited_count, bonus_sum
