# app.py
#
# Общий веб-сервер + выдача миниапа + API + Telegram-бот.
# Запускается на Render как Web Service.

import threading
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
import os

from loader import bot
from bot import register_all_handlers

# -------------------------------
# 1) Запуск Telegram-бота в отдельном потоке
# -------------------------------

def start_bot():
    register_all_handlers()
    print("🤖 Telegram bot started (polling mode)")
    bot.infinity_polling(timeout=30, skip_pending=True)

bot_thread = threading.Thread(target=start_bot, daemon=True)
bot_thread.start()


# -------------------------------
# 2) Запуск FastAPI приложения
# -------------------------------

app = FastAPI()

# Папка web/ как статика (если понадобится)
app.mount("/static", StaticFiles(directory="web"), name="static")


# -------------------------------
# 3) Рендер HTML миниапа
# -------------------------------

@app.get("/", response_class=HTMLResponse)
def serve_miniapp():
    return FileResponse("web/kling.html")


# -------------------------------
# 4) API эндпоинт (backend.py)
# -------------------------------

from web.backend import process_request    # ты уже это писал

@app.post("/api/process")
async def api_process(req: Request):
    try:
        data = await req.json()
        result = process_request(data)
        return JSONResponse(result)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


# -------------------------------
# 5) Render запускает app через uvicorn
# -------------------------------

if __name__ == "__main__":
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 8000))
    )
