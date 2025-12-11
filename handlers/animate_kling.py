# handlers/animate_kling.py
#
# Анимация Kling — один статус + "анимация загрузки" + ссылка на видео в полном качестве ✨

import time
from telebot import types
from services.billing import consume_tokens_or_limit, format_usage_left_message
from services.kling_service import create_kling_image_to_video, get_kling_task_status

MENU_BUTTONS = [
    "🖼 Создать картинку по описанию",
    "📸 Обработать моё фото",
    "🎞 Оживить картинку",
    "👤 Мой тариф и баланс",
]


def register_kling_animation_handlers(bot):

    @bot.message_handler(func=lambda m: m.text == "🎞 Оживить картинку")
    def start_kling_animation(message: types.Message):
        bot.send_message(
            message.chat.id,
            "🎞 Давай оживим твою картинку.\n\n"
            "Отправь фото или файл-картинку — и мы превратим её в живое волшебное видео."
        )
        bot.register_next_step_handler(message, receive_image)

    def receive_image(message: types.Message):
        chat_id = message.chat.id
        user_id = message.from_user.id

        # Выход по кнопкам меню
        if message.content_type == "text" and message.text in MENU_BUTTONS:
            bot.send_message(chat_id, "Ты вышел из режима анимации.")
            return

        # Проверяем лимит на анимации
        if not consume_tokens_or_limit(user_id, mode="animation"):
            bot.send_message(
                chat_id,
                "⚠️ Похоже, лимит на анимации закончился.\n\n"
                "Загляни в «👤 Мой тариф и баланс», чтобы пополнить магию ✨"
            )
            return

        # Принимаем либо фото, либо файл-картинку
        file_id = None
        if message.photo:
            file_id = message.photo[-1].file_id
        elif message.document and (message.document.mime_type or "").startswith("image/"):
            file_id = message.document.file_id
        else:
            bot.send_message(
                chat_id,
                "Мне нужно именно изображение 🙂\n"
                "Отправь фото или файл-картинку (jpg/png/webp)."
            )
            bot.register_next_step_handler(message, receive_image)
            return

        # Получаем URL файла
        file_info = bot.get_file(file_id)
        image_url = f"https://api.telegram.org/file/bot{bot.token}/{file_info.file_path}"

        bot.send_message(
            chat_id,
            "✨ Супер! Теперь напиши пару слов — как должна ожить картинка.\n\n"
            "Например:\n"
            "• «камера медленно приближается»\n"
            "• «лёгкое дыхание света и тени»\n"
            "• «магический живой параллакс»"
        )

        bot.register_next_step_handler(
            message,
            lambda msg: process_prompt(msg, image_url)
        )

    def process_prompt(message: types.Message, image_url: str):
        chat_id = message.chat.id
        user_id = message.from_user.id

        # Выход по кнопкам меню
        if message.content_type == "text" and message.text in MENU_BUTTONS:
            bot.send_message(chat_id, "Ты вышел из режима анимации.")
            return

        prompt = (message.text or "").strip() if message.content_type == "text" else ""
        if not prompt:
            bot.send_message(
                chat_id,
                "Напиши, пожалуйста, хотя бы пару слов — как должна двигаться картинка 🙂"
            )
            bot.register_next_step_handler(message, lambda msg: process_prompt(msg, image_url))
            return

        # Пытаемся создать задачу в Kling
        try:
            task_id = create_kling_image_to_video(prompt=prompt, image_url=image_url)
        except Exception as e:
            bot.send_message(
                chat_id,
                f"Что-то пошло не так при запуске анимации 😔\n"
                f"Текст ошибки: {e}"
            )
            return

        # Одно статусное сообщение, которое будем редактировать
        status_msg = bot.send_message(
            chat_id,
            "🪄 Я отправил твою картинку в волшебную очередь...\n"
            "Чуть-чуть терпения ✨"
        )

        # Кадры для "анимации загрузки"
        submitted_frames = [
            "🪄 Твоя картинка в волшебной очереди\n\nЖдём её звёздной минуты ✨",
            "🪄 Твоя картинка в волшебной очереди.\n\nЖдём её звёздной минуты ✨",
            "🪄 Твоя картинка в волшебной очереди..\n\nЖдём её звёздной минуты ✨",
            "🪄 Твоя картинка в волшебной очереди...\n\nЖдём её звёздной минуты ✨",
        ]

        processing_frames = [
            "✨ Волшебники уже колдуют над твоей картинкой\n\nВнутри всё начинает оживать 🪄",
            "✨ Волшебники уже колдуют над твоей картинкой.\n\nВнутри всё начинает оживать 🪄",
            "✨ Волшебники уже колдуют над твоей картинкой..\n\nВнутри всё начинает оживать 🪄",
            "✨ Волшебники уже колдуют над твоей картинкой...\n\nВнутри всё начинает оживать 🪄",
        ]

        submitted_idx = 0
        processing_idx = 0

        max_attempts = 40
        delay = 6

        for _ in range(max_attempts):
            try:
                status, video_url = get_kling_task_status(task_id)
            except Exception as e:
                try:
                    bot.edit_message_text(
                        f"😔 Не получилось узнать, как там наша анимация.\n"
                        f"Ошибка: {e}",
                        chat_id,
                        status_msg.message_id,
                    )
                except Exception:
                    bot.send_message(
                        chat_id,
                        f"😔 Не получилось узнать, как там наша анимация.\nОшибка: {e}"
                    )
                return

            status = (status or "").lower()
            print("Kling status:", status)

            # Очередь — крутим анимацию ожидания
            if status in ("submitted", "queued", "pending", "unknown"):
                frame = submitted_frames[submitted_idx % len(submitted_frames)]
                submitted_idx += 1
                try:
                    bot.edit_message_text(frame, chat_id, status_msg.message_id)
                except Exception:
                    pass

            # Обработка — крутим анимацию "волшебники колдуют"
            elif status in ("processing", "running"):
                frame = processing_frames[processing_idx % len(processing_frames)]
                processing_idx += 1
                try:
                    bot.edit_message_text(frame, chat_id, status_msg.message_id)
                except Exception:
                    pass

            # Успех — видео готово
            elif status in ("succeed", "success", "completed"):
                try:
                    bot.edit_message_text(
                        "🎞 Готово! Загружаю твоё волшебное видео... ✨",
                        chat_id,
                        status_msg.message_id,
                    )
                except Exception:
                    pass

                if not video_url:
                    bot.send_message(
                        chat_id,
                        "Видео вроде бы готово, но я не смог найти ссылку на него 😔"
                    )
                    return

                caption_html = (
                    "🎞 Готово! Вот твоё маленькое волшебное видео ✨\n\n"
                    f"🔗 <a href=\"{video_url}\">Видео в полном качестве</a>"
                )

                # Пытаемся отправить как видео с подписью и ссылкой
                try:
                    bot.send_video(
                        chat_id,
                        video_url,
                        caption=caption_html,
                        parse_mode="HTML",
                    )
                except Exception:
                    # Если не получилось как видео — хотя бы текст с кликабельной ссылкой
                    bot.send_message(
                        chat_id,
                        caption_html,
                        parse_mode="HTML",
                    )

                # Показываем остаток лимита
                try:
                    bot.send_message(
                        chat_id,
                        format_usage_left_message(user_id),
                        parse_mode="Markdown",
                    )
                except Exception:
                    pass

                return

            # Ошибка/провал
            elif status in ("failed", "error"):
                try:
                    bot.edit_message_text(
                        "😔 Волшебная машина анимации не справилась.\n"
                        "Попробуй ещё раз позже или с другой картинкой.",
                        chat_id,
                        status_msg.message_id,
                    )
                except Exception:
                    bot.send_message(
                        chat_id,
                        "😔 Волшебная машина анимации не справилась.\n"
                        "Попробуй ещё раз позже или с другой картинкой."
                    )
                return

            time.sleep(delay)

        # Таймаут — слишком долго не получили результат
        try:
            bot.edit_message_text(
                "⏳ Сегодня волшебники слишком заняты, и мы не дождались видео вовремя.\n"
                "Попробуй ещё раз немного позже 🪄",
                chat_id,
                status_msg.message_id,
            )
        except Exception:
            bot.send_message(
                chat_id,
                "⏳ Сегодня волшебники слишком заняты, и мы не дождались видео вовремя.\n"
                "Попробуй ещё раз немного позже 🪄",
            )