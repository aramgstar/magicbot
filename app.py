import os
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from telebot import types as tg_types

from loader import bot
from bot import register_all_handlers
from config import TELEGRAM_WEBHOOK_BASE, TELEGRAM_WEBHOOK_PATH

# Миниап backend (твой router)
from web.backend import router as kling_router

app = FastAPI()

# статика миниапа
app.mount("/static", StaticFiles(directory="web"), name="static")

# подключаем API роуты миниапа
app.include_router(kling_router)

# регистрируем хендлеры бота
register_all_handlers()


@app.on_event("startup")
def on_startup():
    """
    Включаем webhook.
    ВАЖНО: на Render НЕ запускаем polling, иначе будет 409 Conflict.
    """
    if not TELEGRAM_WEBHOOK_BASE:
        # Если не задано — бот НЕ сможет получать апдейты
        print("⚠️ TELEGRAM_WEBHOOK_BASE is empty. Set it in Render Env.")
        return

    webhook_url = f"{TELEGRAM_WEBHOOK_BASE}{TELEGRAM_WEBHOOK_PATH}"
    try:
        bot.remove_webhook()
    except Exception:
        pass

    ok = bot.set_webhook(url=webhook_url)
    print(f"✅ Webhook set: {webhook_url} (ok={ok})")


@app.get("/", response_class=HTMLResponse)
def index():
    # твой миниап
    return FileResponse("web/kling.html")


@app.post(TELEGRAM_WEBHOOK_PATH)
async def telegram_webhook(request: Request):
    """
    Telegram будет слать сюда апдейты.
    """
    data = await request.json()
    update = tg_types.Update.de_json(data)
    bot.process_new_updates([update])
    return {"ok": True}