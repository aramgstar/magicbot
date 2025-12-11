# handlers/magic_photo.py
#
# Генерация и обработка фото через NanoBanana PRO:
# - "🖼 Создать картинку по описанию"
# - "📸 Обработать моё фото" (одно фото или Remix до 5 фото)
#
# Логика "📸 Обработать моё фото":
# 1) Пользователь нажимает кнопку.
# 2) Бот просит отправить фото/файл-картинку.
# 3) После первого изображения:
#    - спрашиваем формат (aspect ratio),
#    - пишем:
#      ✅ N изображений добавлено...
# Если изображение одно -> обычная обработка.
# Если 2–5 изображений -> Remix (общая сцена).
#
# Ссылки на оригинал скрыты в HTML-гиперссылке:
# 🔗 <a href="URL">Оригинал в полном разрешении</a>
#
# Дополнительно:
# - при генерации и обработке есть одно "статусное" сообщение,
#   которое обновляется (как у анимации Kling), но без лишних наворотов,
#   чтобы ничего не сломать.

from telebot import types
from services.nanobanana_service import (
    generate_image,
    generate_image_from_url,
    generate_scene_from_urls,
)
from services.billing import consume_tokens_or_limit, format_usage_left_message

# Настройки пользователей
user_aspect_ratio = {}   # user_id -> "1:1" / "9:16" / "16:9" / "3:4"

# Сессии обработки фото для Remix: user_id -> { "images": [file_id,...], "aspect": "1:1" }
photo_sessions = {}


def _aspect_human(aspect: str) -> str:
    """
    Возвращает человекочитаемое описание формата.
    """
    mapping = {
        "1:1": "квадрат",
        "9:16": "вертикально / сторис",
        "16:9": "горизонтально / фильм",
        "3:4": "пост",
    }
    return mapping.get(aspect, "")


def _aspect_caption_line(aspect: str) -> str:
    """
    Строка для подписи к изображению.
    """
    desc = _aspect_human(aspect)
    if desc:
        return f"Формат: {aspect} ({desc})"
    return f"Формат: {aspect}"


def _make_aspect_keyboard() -> types.InlineKeyboardMarkup:
    """
    Инлайн-клавиатура с форматами и подсказками.
    """
    kb = types.InlineKeyboardMarkup()
    kb.add(
        types.InlineKeyboardButton("1:1 • квадрат", callback_data="ar:1:1"),
        types.InlineKeyboardButton("9:16 • вертикально/сторис", callback_data="ar:9:16"),
    )
    kb.add(
        types.InlineKeyboardButton("16:9 • горизонтально/фильм", callback_data="ar:16:9"),
        types.InlineKeyboardButton("3:4 • пост", callback_data="ar:3:4"),
    )
    return kb


def register_magic_photo_handlers(bot):
    """
    Регистрируем хендлеры, связанные с генерацией и обработкой фото.
    Вызывается из bot.py: register_magic_photo_handlers(bot)
    """

    MENU_BUTTONS = [
        "🖼 Создать картинку по описанию",
        "📸 Обработать моё фото",
        "🎞 Оживить картинку",
        "👤 Мой тариф и баланс",
    ]

    # =========================================================
    # Общий callback: выбор aspect ratio
    # =========================================================

    @bot.callback_query_handler(func=lambda c: c.data.startswith("ar:"))
    def cb_aspect_ratio(call: types.CallbackQuery):
        user_id = call.from_user.id
        _, aspect = call.data.split(":", 1)  # "ar:1:1" -> "1:1"

        user_aspect_ratio[user_id] = aspect

        # если у пользователя есть сессия обработки фото — обновим и там
        session = photo_sessions.get(user_id)
        if session is not None:
            session["aspect"] = aspect

        human = _aspect_human(aspect)
        if human:
            msg = f"Формат: {aspect} ({human})"
        else:
            msg = f"Формат: {aspect}"

        bot.answer_callback_query(call.id, msg)

    # =========================================================
    # 1) ГЕНЕРАЦИЯ КАРТИНКИ ПО ОПИСАНИЮ ("🖼")
    # =========================================================

    @bot.message_handler(func=lambda m: m.text == "🖼 Создать картинку по описанию")
    def start_create_by_prompt(message: types.Message):
        chat_id = message.chat.id
        user_id = message.from_user.id

        user_aspect_ratio[user_id] = "1:1"

        markup = _make_aspect_keyboard()

        bot.send_message(
            chat_id,
            "✏️ Напиши описание картинки (промпт).\n\n"
            "Можешь выбрать формат (aspect ratio) с кнопок ниже:\n"
            "• 1:1 — квадрат\n"
            "• 9:16 — вертикально / сторис\n"
            "• 16:9 — горизонтально / фильм\n"
            "• 3:4 — пост\n\n"
            "По умолчанию стоит 1:1.",
            reply_markup=markup,
        )

        bot.register_next_step_handler(message, receive_prompt_for_generation)

    def receive_prompt_for_generation(message: types.Message):
        chat_id = message.chat.id
        user_id = message.from_user.id

        if message.content_type == "text" and message.text in MENU_BUTTONS:
            bot.send_message(
                chat_id,
                "Ты вышел из режима генерации по описанию.\n"
                "Если захочешь снова — нажми «🖼 Создать картинку по описанию» 🙂"
            )
            return

        prompt = (message.text or "").strip()
        if not prompt:
            bot.send_message(chat_id, "Напиши, пожалуйста, текст-описание картинки 🙂")
            bot.register_next_step_handler(message, receive_prompt_for_generation)
            return

        if not consume_tokens_or_limit(user_id, mode="image"):
            bot.send_message(
                chat_id,
                "⚠️ Недостаточно лимита для генерации изображения.\n\n"
                "Загляни в «👤 Мой тариф и баланс», чтобы пополнить или обновить тариф ✨"
            )
            return

        aspect = user_aspect_ratio.get(user_id, "1:1")
        aspect_line = _aspect_caption_line(aspect)

        # Статусное сообщение, которое будем обновлять
        status_msg = bot.send_message(
            chat_id,
            "🪄 Я принял твой запрос и начинаю колдовать над картинкой...\n"
            "Немного подождём, пока магия сработает ✨"
        )

        try:
            img_bytes, img_url = generate_image(
                prompt=prompt,
                resolution="2K",
                aspect=aspect,
                return_url=True,
            )
        except Exception as e:
            # Обновим статус, что магия не сработала
            try:
                bot.edit_message_text(
                    "😔 Магия с картинкой не сработала.\n"
                    "Попробуй ещё раз чуть позже или измени запрос.",
                    chat_id,
                    status_msg.message_id,
                )
            except Exception:
                pass

            bot.send_message(
                chat_id,
                f"Не удалось создать изображение 😔\nОшибка: {e}"
            )
            return

        # Обновляем статус: всё получилось
        try:
            bot.edit_message_text(
                "🎨 Магия сработала! Отправляю твою картинку ✨",
                chat_id,
                status_msg.message_id,
            )
        except Exception:
            pass

        caption = (
            "Готово! ✨\n"
            f"{aspect_line}\n\n"
            f"🔗 <a href=\"{img_url}\">Оригинал в полном разрешении</a>"
        )

        bot.send_photo(chat_id, img_bytes, caption=caption, parse_mode="HTML")

        try:
            bot.send_message(
                chat_id,
                format_usage_left_message(user_id),
                parse_mode="Markdown",
            )
        except Exception:
            pass

    # =========================================================
    # 2) ОБРАБОТКА ФОТО ("📸 Обработать моё фото") + Remix
    # =========================================================

    @bot.message_handler(func=lambda m: m.text == "📸 Обработать моё фото")
    def start_photo_flow(message: types.Message):
        """
        Старт сценария обработки фото:
        1) Просим первое изображение (фото или файл-картинку).
        """
        chat_id = message.chat.id
        user_id = message.from_user.id

        photo_sessions[user_id] = {
            "images": [],
            "aspect": "1:1",
        }
        user_aspect_ratio[user_id] = "1:1"

        bot.send_message(
            chat_id,
            "📸 Отправьте изображение, которое хотите обработать.\n\n"
            "Можно отправить одно изображение, а можно несколько подряд — "
            "потом я смогу собрать их в общую сцену (режим Remix)."
        )

        bot.register_next_step_handler(message, collect_photos_step)

    def collect_photos_step(message: types.Message):
        """
        Сбор изображений: до 5 штук.
        Принимаем:
        - обычные фото (message.photo)
        - документы-картинки (message.document с mime_type image/*)
        Первое изображение может быть файлом.
        После первого изображения — спрашиваем формат.
        Если приходит текст и есть хотя бы одно изображение — считаем это промптом.
        """
        chat_id = message.chat.id
        user_id = message.from_user.id

        session = photo_sessions.get(user_id)
        if session is None:
            bot.send_message(
                chat_id,
                "Давай начнём заново 😊 Нажми «📸 Обработать моё фото»."
            )
            return

        # Если пользователь передумал и нажал кнопку меню
        if message.content_type == "text" and message.text in MENU_BUTTONS:
            photo_sessions.pop(user_id, None)
            bot.send_message(
                chat_id,
                "Ты вышел из режима обработки фото.\n"
                "Если захочешь снова — нажми «📸 Обработать моё фото» 🙂"
            )
            return

        # Если пришёл текст и уже есть изображения — это промпт
        if message.content_type == "text" and session["images"]:
            prompt = (message.text or "").strip()
            if not prompt:
                bot.send_message(
                    chat_id,
                    "Напиши, пожалуйста, что нужно сделать с изображением 🙂"
                )
                bot.register_next_step_handler(message, collect_photos_step)
                return

            _process_photo_session_with_prompt(bot, message, prompt, session)
            return

        # Пытаемся извлечь изображение
        file_id = None

        # 1) обычная фотография
        if message.photo:
            file_id = message.photo[-1].file_id

        # 2) документ -> только если это картинка
        elif message.content_type == "document" and message.document:
            mime = message.document.mime_type or ""
            if mime.startswith("image/"):
                file_id = message.document.file_id
            else:
                bot.send_message(
                    chat_id,
                    "Этот файл не является изображением 🤔\n"
                    "Отправьте фото или файл-картинку (jpg/png/webp).\n\n"
                    "Когда закончите добавлять изображения — просто напишите свой запрос."
                )
                bot.register_next_step_handler(message, collect_photos_step)
                return

        else:
            # Не фото и не картинка-файл
            bot.send_message(
                chat_id,
                "Мне нужно изображение 🙂\n"
                "Отправьте фото или файл-картинку (jpg/png/webp).\n\n"
                "Когда закончите добавлять изображения — просто напишите, что хотите сделать."
            )
            bot.register_next_step_handler(message, collect_photos_step)
            return

        # Добавили изображение
        session["images"].append(file_id)
        num = len(session["images"])

        # После первого изображения → спрашиваем формат
        if num == 1:
            markup = _make_aspect_keyboard()
            bot.send_message(
                chat_id,
                "Выберите желаемую пропорцию будущего изображения:\n"
                "• 1:1 — квадрат\n"
                "• 9:16 — вертикально / сторис\n"
                "• 16:9 — горизонтально / фильм\n"
                "• 3:4 — пост",
                reply_markup=markup,
            )

        # Информация о добавленных изображениях
        if num == 1:
            added_text = "✅ 1 изображение добавлено."
        else:
            added_text = f"✅ {num} изображений добавлено."

        if num < 5:
            extra = (
                "\n\nМожете сразу ввести свой запрос — и я начну обработку.\n"
                "Или загрузите ещё до "
                f"{5 - num} изображений, чтобы использовать режим Remix (общая сцена) 👇"
            )
        else:
            extra = (
                "\n\nВы добавили максимум (5 изображений).\n"
                "Теперь напишите, что нужно сделать — и я создам общую сцену (режим Remix) 👇"
            )

        bot.send_message(chat_id, added_text + extra)

        # Ждём следующее изображение или текст
        bot.register_next_step_handler(message, collect_photos_step)

    # =========================================================
    # Внутренняя функция: запуск обработки (одно фото / Remix)
    # =========================================================

    def _process_photo_session_with_prompt(bot, message: types.Message, prompt: str, session: dict):
        chat_id = message.chat.id
        user_id = message.from_user.id

        images = session.get("images") or []
        if not images:
            bot.send_message(
                chat_id,
                "Не вижу добавленных изображений 🤔\n"
                "Нажми «📸 Обработать моё фото» и отправь хотя бы одно изображение."
            )
            photo_sessions.pop(user_id, None)
            return

        aspect = session.get("aspect") or user_aspect_ratio.get(user_id, "1:1")
        aspect_line = _aspect_caption_line(aspect)

        # проверяем лимит
        if not consume_tokens_or_limit(user_id, mode="image"):
            bot.send_message(
                chat_id,
                "⚠️ Недостаточно лимита для обработки фото.\n\n"
                "Загляни в «👤 Мой тариф и баланс», чтобы пополнить или обновить тариф ✨"
            )
            photo_sessions.pop(user_id, None)
            return

        count = len(images)

        # Статусное сообщение
        if count == 1:
            status_msg = bot.send_message(
                chat_id,
                "🪄 Я взял твоё изображение и начинаю аккуратно его преображать...\n"
                "Немного подождём, пока сработает магия ✨"
            )
        else:
            status_msg = bot.send_message(
                chat_id,
                f"🪄 Я собрал {count} твоих изображений и готовлю из них общую сцену (Remix)...\n"
                "Немного подождём, пока мир сложится в одну картинку ✨"
            )

        # Собираем URL'ы изображений и запускаем обработку
        try:
            file_urls = []
            for fid in images:
                file_info = bot.get_file(fid)
                file_path = file_info.file_path
                file_url = f"https://api.telegram.org/file/bot{bot.token}/{file_path}"
                file_urls.append(file_url)

            if count == 1:
                img_bytes, img_url = generate_image_from_url(
                    image_url=file_urls[0],
                    prompt=prompt,
                    resolution="2K",
                    aspect=aspect,
                    return_url=True,
                )
                title_line = "Готово! ✨ Обработано 1 изображение."
            else:
                img_bytes, img_url = generate_scene_from_urls(
                    image_urls=file_urls,
                    prompt=prompt,
                    resolution="2K",
                    aspect=aspect,
                    return_url=True,
                )
                title_line = f"Готово! ✨ Режим Remix: общая сцена из {count} изображений."

        except Exception as e:
            # Обновляем статус — магия не сработала
            try:
                bot.edit_message_text(
                    "😔 Магия с обработкой не сработала.\n"
                    "Попробуй ещё раз чуть позже или с другими параметрами.",
                    chat_id,
                    status_msg.message_id,
                )
            except Exception:
                pass

            bot.send_message(
                chat_id,
                f"Не удалось обработать изображение 😔\nОшибка: {e}"
            )
            photo_sessions.pop(user_id, None)
            return

        # Магия удалась — обновим статус
        try:
            bot.edit_message_text(
                "🎨 Магия сработала! Отправляю результат ✨",
                chat_id,
                status_msg.message_id,
            )
        except Exception:
            pass

        caption = (
            f"{title_line}\n"
            f"{aspect_line}\n\n"
            f"🔗 <a href=\"{img_url}\">Оригинал в полном разрешении</a>"
        )

        bot.send_photo(chat_id, img_bytes, caption=caption, parse_mode="HTML")

        # остаток лимита
        try:
            bot.send_message(
                chat_id,
                format_usage_left_message(user_id),
                parse_mode="Markdown",
            )
        except Exception:
            pass

        # очищаем сессию
        photo_sessions.pop(user_id, None)