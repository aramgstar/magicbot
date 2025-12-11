# task_worker.py

import time
import traceback
from io import BytesIO

import requests

from loader import bot
from utils.tasks import (
    get_all_pending_generations,
    remove_pending_generation,
    create_task,
)
# Эту функцию мы уже исправили в nanobanana_service.py
from services.nanobanana_service import check_generation_task 


def _process_pending_generation(gen: dict):
    nb_task_id = gen["nb_task_id"]
    user_id = gen["user_id"]
    chat_id = gen["chat_id"]
    prompt = gen["prompt"]
    model = gen["model"]

    try:
        # Получаем статус в формате: {"status": "processing"|"success"|"error", "url": "..."|"msg": "..."}
        status_info = check_generation_task(nb_task_id)
    except Exception as e:
        print(f"⚠️ Error checking NanoBanana task {nb_task_id}: {e}")
        traceback.print_exc()
        return  # попробуем ещё в следующем цикле

    current_status = status_info.get("status")

    # 1. Ещё генерится
    if current_status == "processing":
        return

    # 2. Ошибка
    if current_status == "error":
        error_msg = status_info.get("msg", "Неизвестная ошибка.")
        bot.send_message(
            chat_id,
            f"Не удалось создать изображение 😔\n\n"
            f"Техническая ошибка: {error_msg}",
        )
        remove_pending_generation(nb_task_id)
        return

    # 3. Успех (current_status == "success")
    
    image_url = status_info.get("url")
    if not image_url:
        bot.send_message(
            chat_id,
            "Изображение почти было готово, но не удалось получить ссылку 😔",
        )
        remove_pending_generation(nb_task_id)
        return

    try:
        resp = requests.get(image_url, timeout=60)
        resp.raise_for_status()
        image_bytes = resp.content
    except Exception as e:
        print(f"⚠️ Error downloading image from {image_url}: {e}")
        traceback.print_exc()
        bot.send_message(
            chat_id,
            "Изображение сгенерировалось, но не получилось его скачать 😔\n"
            "Попробуй, пожалуйста, ещё раз.",
        )
        remove_pending_generation(nb_task_id)
        return

    # создаём внутреннюю задачу для анимации
    internal_task_id = create_task(prompt, image_bytes, user_id)

    from telebot import types
    kb = types.InlineKeyboardMarkup()
    kb.add(
        types.InlineKeyboardButton(
            "✨ Анимировать", callback_data=f"animate:{internal_task_id}"
        )
    )

    bio = BytesIO(image_bytes)
    bio.name = "image.png"

    # Строка 92 (bot.send_photo) - теперь она должна быть корректно закрыта.
    bot.send_photo(
        chat_id,
        bio,
        caption="Готово ✨ Вот ваша магическая картинка!\n"
                "Можете анимировать её кнопкой ниже.",
        reply_markup=kb,
    )

    remove_pending_generation(nb_task_id)


def _worker_loop():
    """
    Фоновый цикл: каждые несколько секунд опрашивает все незавершённые задачи.
    """
    print("🛠️ Background NanoBanana worker started")
    while True:
        try:
            pending = get_all_pending_generations()
            if pending:
                print(f"🔍 Checking {len(pending)} NanoBanana tasks...")
            for gen in pending:
                _process_pending_generation(gen)
        except Exception as e:
            print(f"⚠️ Worker loop error: {e}")
            traceback.print_exc()

        time.sleep(3)


def start_background_worker():
    """
    Запускает воркер в отдельном потоке (daemon).
    Вызывается один раз из bot.py.
    """
    import threading

    t = threading.Thread(target=_worker_loop, daemon=True)
    t.start()
