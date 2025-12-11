# handlers/menu.py

from telebot import types
from services.billing import format_balance_message


def build_main_menu():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(types.KeyboardButton("🖼 Создать картинку по описанию"))
    kb.add(types.KeyboardButton("📸 Обработать моё фото"))
    kb.add(types.KeyboardButton("🎞 Оживить картинку"))
    kb.add(types.KeyboardButton("👤 Мой тариф и баланс"))
    return kb


def build_tariffs_keyboard() -> types.InlineKeyboardMarkup:
    """
    Инлайн-клавиатура с тарифами START / PRO / MAX.
    callback_data совпадает с логикой в handlers/payments.py:
    - tariff_start
    - tariff_pro
    - tariff_max
    """
    kb = types.InlineKeyboardMarkup()
    kb.add(
        types.InlineKeyboardButton(
            text="START — 249 ₽",
            callback_data="tariff_start",
        )
    )
    kb.add(
        types.InlineKeyboardButton(
            text="PRO — 499 ₽",
            callback_data="tariff_pro",
        )
    )
    kb.add(
        types.InlineKeyboardButton(
            text="MAX — 949 ₽",
            callback_data="tariff_max",
        )
    )
    return kb


def tariffs_text() -> str:
    """
    Текстовое описание тарифов — простое и понятное.
    """
    return (
        "📦 *Тарифы:*\n\n"
        "*START* — 249 ₽\n"
        "• 124 токена для магии ✨\n\n"
        "*PRO* — 499 ₽\n"
        "• 249 токенов для магии ✨\n\n"
        "*MAX* — 949 ₽\n"
        "• 474 токена для магии ✨\n"
    )


def register_menu_handlers(bot):

    @bot.message_handler(commands=["start"])
    def start_handler(message):
        text = (
            "✨ Я помогу создать волшебные картинки, улучшить фото "
            "и оживить изображения в видео.\n\n"
            "Выбери, с чего начнём:"
        )
        bot.send_message(
            message.chat.id,
            text,
            reply_markup=build_main_menu()
        )

    @bot.message_handler(func=lambda m: m.text == "👤 Мой тариф и баланс")
    def my_tariff_handler(message):
        user_id = message.from_user.id
        balance_text = format_balance_message(user_id)
        kb = build_tariffs_keyboard()

        bot.send_message(
            message.chat.id,
            "👤 *Твой тариф и баланс:*\n\n"
            f"{balance_text}\n\n"
            f"{tariffs_text()}",
            parse_mode="Markdown",
            reply_markup=kb,
        )