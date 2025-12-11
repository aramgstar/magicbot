# handlers/admin_handler.py
#
# Максимальная информативная админ-панель для ChudoMaster.
# Доступ только для admin_id.
#
# Показывает:
# - количество пользователей
# - количество покупок
# - покупки за сегодня
# - использование промокодов
# - статистику тарифов
# - токен-экономику
# - реферальную статистику

from telebot import types
from services.db import get_conn
from services.billing import get_user_tariff

ADMIN_ID = 13502816  # твой ID


def register_admin_handlers(bot):

    # «/admin» — главная панель администратора
    @bot.message_handler(commands=["admin"])
    def admin_panel(message):
        if message.from_user.id != ADMIN_ID:
            return

        stats = _collect_stats()

        text = (
            "👑 *Админ-панель ChudoMaster*\n\n"
            f"📌 Пользователей: *{stats['users']}*\n"
            f"💳 Покупок всего: *{stats['purchases_total']}*\n"
            f"💳 Покупок сегодня: *{stats['purchases_today']}*\n"
            f"🎁 Активировано промокодов: *{stats['promocodes_used']}*\n\n"
            "👥 *Реферальная система:*\n"
            f"— Пользователей с рефералами: *{stats['ref_users']}*\n"
            f"— Всего бонусов рефералам: *{stats['ref_bonus_total']}* токенов\n\n"
            "🔮 *Токен-экономика:*\n"
            f"— Всего начислено токенов: *{stats['tokens_added_total']}*\n"
            f"— Средний баланс: *{stats['avg_balance']}*\n\n"
            "📦 *Тарифы (кол-во покупок):*\n"
            f"— START: *{stats['tariff_start']}*\n"
            f"— PRO: *{stats['tariff_pro']}*\n"
            f"— MAX: *{stats['tariff_max']}*\n"
        )

        kb = types.InlineKeyboardMarkup()
        kb.add(
            types.InlineKeyboardButton("📄 Последние покупки", callback_data="admin_last_purchases"),
        )
        kb.add(
            types.InlineKeyboardButton("👥 Пользователи", callback_data="admin_users"),
        )
        kb.add(
            types.InlineKeyboardButton("🎁 Промокоды", callback_data="admin_promos"),
        )
        kb.add(
            types.InlineKeyboardButton("🔗 Рефералы", callback_data="admin_refs"),
        )

        bot.send_message(
            message.chat.id,
            text,
            parse_mode="Markdown",
            reply_markup=kb
        )

    # ================================
    # КНОПКИ АДМИНКИ
    # ================================

    @bot.callback_query_handler(func=lambda c: c.data == "admin_last_purchases")
    def cb_last_purchases(call):
        if call.from_user.id != ADMIN_ID:
            return

        conn = get_conn()
        cur = conn.cursor()
        cur.execute("""
            SELECT user_id, tariff_key, amount_rub, tokens_added, created_at
            FROM purchases
            ORDER BY id DESC
            LIMIT 20
        """)
        rows = cur.fetchall()
        conn.close()

        if not rows:
            bot.answer_callback_query(call.id, "Покупок ещё нет")
            return

        text = "📄 *Последние покупки:*\n\n"
        for r in rows:
            text += (
                f"👤 User: {r['user_id']}\n"
                f"Тариф: {r['tariff_key'].upper()}\n"
                f"Сумма: {r['amount_rub']}₽\n"
                f"Токенов начислено: {r['tokens_added']}\n"
                f"⏱ {r['created_at']}\n\n"
            )

        bot.send_message(call.message.chat.id, text, parse_mode="Markdown")

    @bot.callback_query_handler(func=lambda c: c.data == "admin_users")
    def cb_users(call):
        if call.from_user.id != ADMIN_ID:
            return

        conn = get_conn()
        cur = conn.cursor()
        cur.execute("SELECT user_id FROM users")
        rows = cur.fetchall()
        conn.close()

        text = f"👥 *Пользователи ({len(rows)}):*\n\n"
        text += "\n".join(str(r["user_id"]) for r in rows)

        bot.send_message(call.message.chat.id, text, parse_mode="Markdown")

    @bot.callback_query_handler(func=lambda c: c.data == "admin_promos")
    def cb_promos(call):
        if call.from_user.id != ADMIN_ID:
            return

        conn = get_conn()
        cur = conn.cursor()
        cur.execute("""
            SELECT code, COUNT(user_id) AS used
            FROM user_promo_usage
            GROUP BY code
        """)
        rows = cur.fetchall()
        conn.close()

        if not rows:
            bot.send_message(call.message.chat.id, "🎁 Промокоды ещё никто не активировал.")
            return

        text = "🎁 *Статистика промокодов:*\n\n"
        for r in rows:
            text += f"Код: *{r['code']}* — использован: *{r['used']}* раз(а)\n"

        bot.send_message(call.message.chat.id, text, parse_mode="Markdown")

    @bot.callback_query_handler(func=lambda c: c.data == "admin_refs")
    def cb_refs(call):
        if call.from_user.id != ADMIN_ID:
            return

        conn = get_conn()
        cur = conn.cursor()
        cur.execute("""
            SELECT referrer_id, invited_id, reward_referrer, created_at
            FROM referrals
            ORDER BY id DESC
            LIMIT 50
        """)
        rows = cur.fetchall()
        conn.close()

        if not rows:
            bot.send_message(call.message.chat.id, "🔗 Пока нет рефералов.")
            return

        text = "🔗 *Рефералы:*\n\n"
        for r in rows:
            text += (
                f"👤 Пригласил: {r['referrer_id']} → Новый: {r['invited_id']}\n"
                f"🎁 Бонус: {r['reward_referrer']} токенов\n"
                f"⏱ {r['created_at']}\n\n"
            )

        bot.send_message(call.message.chat.id, text, parse_mode="Markdown")


# ================================================
# 🔍 Сбор статистики
# ================================================
def _collect_stats():
    conn = get_conn()
    cur = conn.cursor()

    # пользователи
    cur.execute("SELECT COUNT(*) FROM users")
    users = cur.fetchone()[0]

    # покупки
    cur.execute("SELECT COUNT(*) FROM purchases")
    purchases_total = cur.fetchone()[0]

    # покупки за сегодня
    cur.execute("SELECT COUNT(*) FROM purchases WHERE date(created_at)=date('now')")
    purchases_today = cur.fetchone()[0]

    # использованные промокоды
    cur.execute("SELECT COUNT(*) FROM user_promo_usage")
    promocodes_used = cur.fetchone()[0]

    # тарифы
    cur.execute("SELECT COUNT(*) FROM purchases WHERE tariff_key='start'")
    tariff_start = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM purchases WHERE tariff_key='pro'")
    tariff_pro = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM purchases WHERE tariff_key='max'")
    tariff_max = cur.fetchone()[0]

    # рефералы
    cur.execute("SELECT COUNT(DISTINCT referrer_id) FROM referrals")
    ref_users = cur.fetchone()[0]

    cur.execute("SELECT SUM(reward_referrer) FROM referrals")
    ref_bonus_total = cur.fetchone()[0] or 0

    # токены
    cur.execute("SELECT SUM(balance) FROM tokens")
    tokens_total = cur.fetchone()[0] or 0

    cur.execute("SELECT AVG(balance) FROM tokens")
    avg_balance = int(cur.fetchone()[0] or 0)

    conn.close()

    return {
        "users": users,
        "purchases_total": purchases_total,
        "purchases_today": purchases_today,
        "promocodes_used": promocodes_used,
        "tariff_start": tariff_start,
        "tariff_pro": tariff_pro,
        "tariff_max": tariff_max,
        "ref_users": ref_users,
        "ref_bonus_total": ref_bonus_total,
        "tokens_added_total": tokens_total,
        "avg_balance": avg_balance,
    }
