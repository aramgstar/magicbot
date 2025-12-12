# app.py
#
# Общий веб-сервер + миниап + простая заглушка backend-а
# + запуск Telegram-бота в отдельном потоке.

import os
import threading

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from loader import bot
from bot import register_all_handlers


# -------------------------------
# 1) Запуск Telegram-бота
# -------------------------------

def start_bot():
    register_all_handlers()
    print("🤖 Telegram bot started (polling mode from app.py)")
    bot.infinity_polling(timeout=30, skip_pending=True)


bot_thread = threading.Thread(target=start_bot, daemon=True)
bot_thread.start()


# -------------------------------
# 2) FastAPI-приложение
# -------------------------------

app = FastAPI()

# статика из папки web/ (если что-то ещё добавишь)
app.mount("/static", StaticFiles(directory="web"), name="static")


# -------------------------------
# 3) Главная страница: миниап
# -------------------------------

@app.get("/", response_class=HTMLResponse)
def index():
    # отдаём web/kling.html
    return FileResponse("web/kling.html")


# -------------------------------
# 4) Заглушка backend для миниапа
#    чтобы деплой не падал и запросы не ломались
# -------------------------------

@app.post("/api/kling_effect")
async def kling_effect_stub(request: Request):
    """
    Временный заглушечный endpoint.
    Миниап может слать сюда FormData (effect_id, prompt, photo).
    Пока просто возвращаем echo-ответ, чтобы всё работало без ошибок.
    """
    form = await request.form()
    fields = {k: (str(v)[:50]) for k, v in form.items()}

    return JSONResponse(
        {
            "ok": True,
            "message": "Backend-заглушка на Render. Kling пока не подключен к миниапу.",
            "received_fields": list(fields.keys()),
        }
    )


# -------------------------------
# 5) Локальный запуск (не используется Render-ом)
# -------------------------------

if __name__ == "__main__":
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 8000)),
        reload=True,
    )
