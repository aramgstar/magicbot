# handlers/idea_flow.py
#
# Создание картинки по описанию:
# кнопка "🖼 Создать картинку по описанию" ->
# просим текст ->
# генерируем картинку через NanoBanana ->
# списываем генерацию через billing и показываем остаток.

from telebot import types
from services.nanobanana_service import generate_image
from services.billing import (
    can_use_image,
    register_image_usage,
    format_usage_left_message,
)


def register_idea_handlers(bot):
    @bot.message_handler(func=lambda m: m.text == "🖼 Создать картинку по описанию")
    def idea_start(message: types.Message):
        bot.send_message(
            message.chat.id,
            "🪄 Давай создадим картинку!\n\n"
            "Напиши простыми словами, что ты хочешь увидеть.\n"
            "Например:\n"
            "• «дом в лесу зимой»\n"
            "• «кот-волшебник в шляпе»\n"
            "• «семья за праздничным столом»"
        )
        bot.register_next_step_handler(message, receive_prompt)

    def receive_prompt(message: types.Message):
        user_id = message.from_user.id
        chat_id = message.chat.id
        prompt = (message.text or "").strip()

        if not prompt:
            bot.send_message(chat_id, "Опиши, пожалуйста, что хочешь увидеть 😊")
            return

        # проверяем, можно ли тратить генерацию
        ok, reason = can_use_image(user_id)
        if not ok:
            bot.send_message(
                chat_id,
                f"⚠️ {reason}\n\n"
                "Ты можешь выбрать или продлить тариф в разделе «👤 Мой тариф и баланс»."
            )
            return

        bot.send_chat_action(chat_id, "upload_photo")
        bot.send_message(chat_id, "✨ Создаю изображение, подожди немного…")

        try:
            # generate_image должна вернуть байты готовой картинки
            image_bytes = generate_image(prompt)
        except Exception as e:
            bot.send_message(
                chat_id,
                "Не удалось создать изображение 😔\n"
                f"Ошибка: {e}"
            )
            return

        # списываем бесплатную генерацию / токены
        register_image_usage(user_id)

        # отправляем картинку
        bot.send_photo(
            chat_id,
            image_bytes,
            caption="Готово! ✨\n\n" + format_usage_left_message(user_id),
            parse_mode="Markdown",
        )
