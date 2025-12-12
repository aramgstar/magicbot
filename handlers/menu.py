# handlers/menu.py

from telebot import types
from services.billing import format_balance_message

# URL твоего миниапа (Render)
MAGICBOT_WEBAPP_URL = "https://magicbot-g98j.onrender.com"


def build_main_menu() -> types.ReplyKeyboardMarkup:
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)

    # Порядок кнопок:
    kb.add(types.KeyboardButton("🖼 Создать картинку по описанию"))
    kb.add(types.KeyboardButton("📸 Обработать моё фото"))
    kb.add(types.KeyboardButton("🎞 Оживить картинку"))
    kb.add(types.KeyboardButton("🎄 Видеошаблоны"))
    kb.add(types.KeyboardButton("👤 Мой тариф и баланс"))

    return kb


def register_menu_handlers(bot):

    @bot.message_handler(commands=["start", "menu"])
    def start_or_menu_handler(message: types.Message):
        """
        /start и /menu — пересобираем главное меню и отправляем пользователю.
        """
        text = (
            "✨ Я помогу создать волшебные картинки, улучшить фото, "
            "оживить изображения в видео и собрать ролики из шаблонов.\n\n"
            "Выбери, с чего начнём:"
        )
        bot.send_message(
            message.chat.id,
            text,
            reply_markup=build_main_menu(),
        )

    @bot.message_handler(func=lambda m: m.text == "👤 Мой тариф и баланс")
    def my_tariff_handler(message: types.Message):
        """
        Показываем баланс + тарифы.
        Импортируем payments лениво, чтобы ошибка в оплатах
        не ломала всё меню.
        """
        user_id = message.from_user.id
        balance_text = format_balance_message(user_id)

        kb = None
        tariffs_block = ""

        try:
            from handlers.payments import build_tariffs_keyboard, tariffs_text

            kb = build_tariffs_keyboard()
            tariffs_block = tariffs_text()
        except Exception:
            # если с оплатами что-то не так — просто не показываем кнопки покупки
            tariffs_block = (
                "⚠️ Тарифы временно недоступны.\n"
                "Я сообщу тебе, когда магию оплат починим ✨"
            )

        bot.send_message(
            message.chat.id,
            "👤 *Твой тариф и баланс:*\n\n"
            f"{balance_text}\n\n"
            f"{tariffs_block}",
            parse_mode="Markdown",
            reply_markup=kb,
        )

    @bot.message_handler(func=lambda m: m.text == "🎄 Видеошаблоны")
    def open_magic_templates(message: types.Message):
        """
        Открываем миниап с шаблонами через WebApp.
        """
        kb = types.InlineKeyboardMarkup()
        webapp = types.WebAppInfo(url=MAGICBOT_WEBAPP_URL)

        kb.add(
            types.InlineKeyboardButton(
                text="✨ Открыть видеошаблоны",
                web_app=webapp,
            )
        )

        bot.send_message(
            message.chat.id,
            "✨ Сейчас открою окно с видеошаблонами.\n"
            "Они загрузятся прямо внутри Telegram 👇",
            reply_markup=kb,
        )