# app.py
#
# FastAPI сервер для Render:
# - Webhook Telegram: POST /telegram/webhook
# - MiniApp: GET /
# - Backend MiniApp: подключается из web/backend.py (router)
#
# ВАЖНО: тут НЕТ polling. Только webhook.

import os
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from loader import bot
from bot import register_all_handlers
from config import TELEGRAM_WEBHOOK_BASE

# 1) регистрируем хендлеры один раз
register_all_handlers()

app = FastAPI()

# 2) статика (если надо отдавать js/css/картинки)
app.mount("/static", StaticFiles(directory="web"), name="static")

# 3) подключаем backend MiniApp из web/backend.py
# В web/backend.py должен быть router = APIRouter() и @router.post("/api/kling_effect")
from web.backend import router as backend_router
app.include_router(backend_router)


# 4) MiniApp на главной
@app.get("/", response_class=HTMLResponse)
def index():
    return FileResponse("web/kling.html")


# 5) Telegram webhook endpoint
@app.post("/telegram/webhook")
async def telegram_webhook(req: Request):
    update_json = await req.json()
    from telebot.types import Update
    update = Update.de_json(update_json)
    bot.process_new_updates([update])
    return {"ok": True}


# 6) Авто-установка webhook при старте
@app.on_event("startup")
async def on_startup():
    base = (TELEGRAM_WEBHOOK_BASE or "").rstrip("/")
    if not base:
        print("⚠️ TELEGRAM_WEBHOOK_BASE не задан — webhook не установлен.")
        return

    webhook_url = f"{base}/telegram/webhook"

    try:
        bot.remove_webhook()
    except Exception:
        pass

    ok = bot.set_webhook(url=webhook_url)
    print(f"✅ Webhook set: {webhook_url} | result={ok}")