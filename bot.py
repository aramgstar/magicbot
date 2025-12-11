# bot.py
#
# Главная точка входа бота ChudoMaster.
# Работает в режиме POLLING (без вебхуков).
#
# Запуск:
#   cd /Users/aram/Downloads/bot/aimagicbot
#   source venv/bin/activate
#   python bot.py

from loader import bot


def register_all_handlers():
    """
    Подключаем все хендлеры из папки handlers.
    Каждую группу оборачиваем в try/except, чтобы бот не падал,
    если какого-то файла или функции нет.
    """

    # --- Главное меню / базовые команды ---
    try:
        from handlers.menu import register_menu_handlers
        register_menu_handlers(bot)
    except Exception:
        pass

    # --- Магия с фото / NanoBanana ---
    try:
        from handlers.magic_photo import register_magic_photo_handlers
        register_magic_photo_handlers(bot)
    except Exception:
        pass

    # --- Анимация Kling (🎞 Оживить картинку) ---
    try:
        from handlers.animate_kling import register_kling_animation_handlers
        register_kling_animation_handlers(bot)
    except Exception:
        pass

    # --- Идеи / генерация идей (если есть) ---
    try:
        from handlers.idea_flow import register_idea_flow_handlers
        register_idea_flow_handlers(bot)
    except Exception:
        pass

    # --- Платежи / тарифы / успешная оплата ---
    try:
        from handlers.payments import (
            register_payment_handlers,
            register_precheckout,
            register_successful_payment,
        )
        register_payment_handlers(bot)
        register_precheckout(bot)
        register_successful_payment(bot)
    except Exception:
        pass

    # --- Промокоды (/promo) ---
    try:
        from handlers.promocodes_handler import register_promocode_handlers
        register_promocode_handlers(bot)
    except Exception:
        pass

    # --- Рефералка (/ref и старт по реф-ссылке) ---
    try:
        from handlers.referrals_handler import register_referral_handlers
        register_referral_handlers(bot)
    except Exception:
        pass

    # --- Профиль (👤 Мой профиль /profile) ---
    try:
        from handlers.profile_handler import register_profile_handlers
        register_profile_handlers(bot)
    except Exception:
        pass

    # --- Админ-панель (/admin) ---
    try:
        from handlers.admin_handler import register_admin_handlers
        register_admin_handlers(bot)
    except Exception:
        pass

    # --- Общие callback-кнопки (если есть) ---
    try:
        from handlers.callbacks import register_callback_handlers
        register_callback_handlers()
    except Exception:
        pass


def main():
    # Регистрируем все обработчики
    register_all_handlers()

    # На всякий случай отключаем вебхук, чтобы polling не конфликтовал
    try:
        bot.remove_webhook()
    except Exception:
        pass

    print("🚀 BOT STARTED IN POLLING MODE (no webhook)")
    bot.infinity_polling(timeout=30, skip_pending=True)


if __name__ == "__main__":
    main()