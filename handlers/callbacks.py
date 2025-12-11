from telebot import types
from loader import bot   # берём bot из loader.py
from utils.tasks import get_task
from services.kling_service import animate_image


def register_callback_handlers():

    @bot.callback_query_handler(func=lambda c: c.data.startswith("animate:"))
    def cb_animate(call: types.CallbackQuery):
        # Ожидаем формат "animate:<task_id>"
        try:
            _, task_id = call.data.split(":", 1)
        except ValueError:
            bot.answer_callback_query(call.id, "Некорректный формат callback")
            return

        task = get_task(task_id)

        if not task:
            bot.answer_callback_query(call.id, "Не нашёл задачу")
            return

        # Берём prompt из задачи (если нет — подставим дефолт)
        prompt = task.get("prompt") or "cinematic AI animation"

        bot.answer_callback_query(call.id, "✨ Создаю видео из описания...")

        try:
            video_url = animate_image(prompt)
        except Exception as e:
            bot.send_message(
                call.message.chat.id,
                f"Не удалось создать видео 😔\nОшибка: {e}"
            )
            return

        # Отправляем результат
        bot.send_message(
            call.message.chat.id,
            "Готово! 🎞 Я создал анимацию по этому описанию:"
        )
        bot.send_message(call.message.chat.id, f"📝 {prompt}")

        # Если Kling вернул HTTP-URL — TeleBot умеет отправлять его напрямую
        bot.send_video(
            call.message.chat.id,
            video=video_url,
            caption="✨ Вот твоё видео от Kling"
        )
