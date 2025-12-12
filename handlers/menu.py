# handlers/menu.py

from telebot import types
from services.billing import format_balance_message


def build_main_menu():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(types.KeyboardButton("🖼 Создать картинку по описанию"))
    kb.add(types.KeyboardButton("📸 Обработать моё фото"))
    kb.add(types.KeyboardButton("🎞 Оживить картинку"))
    kb.add(types.KeyboardButton("🎄 Видеошаблоны"))
    kb.add(types.KeyboardButton("👤 Мой тариф и баланс"))
    return kb


def register_menu_handlers(bot):

    @bot.message_handler(commands=["start", "menu"])
    def start_handler(message):
        bot.send_message(
            message.chat.id,
            "✨ Выбери, что хочешь сделать:",
            reply_markup=build_main_menu()
        )

    @bot.message_handler(func=lambda m: m.text == "👤 Мой тариф и баланс")
    def my_tariff_handler(message):
        user_id = message.from_user.id
        balance_text = format_balance_message(user_id)

        # ✅ НИКАКИХ заглушек. Импортируем оплату как есть.
        from handlers.payments import build_tariffs_keyboard, tariffs_text

        bot.send_message(
            message.chat.id,
            "👤 *Твой тариф и баланс:*\n\n"
            f"{balance_text}\n\n"
            f"{tariffs_text()}",
            parse_mode="Markdown",
            reply_markup=build_tariffs_keyboard(),
        )