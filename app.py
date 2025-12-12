# app.py
#
# FastAPI сервер:
# - MiniApp: отдаёт web/kling.html на /
# - Backend: /api/kling_effect принимает фото из miniapp и запускает Kling
# - Telegram webhook: /telegram/webhook (без polling => нет 409)
#
# Важно: никакого infinity_polling!

import os
import json
import time
import hmac
import hashlib
import urllib.parse
import shutil
import requests

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from loader import bot
from bot import register_all_handlers
from config import TELEGRAM_TOKEN, TELEGRAM_WEBHOOK_BASE
from services.kling_service import create_kling_image_to_video, poll_kling_result

# 0) Регистрируем хендлеры 1 раз
register_all_handlers()

app = FastAPI()
app.mount("/static", StaticFiles(directory="web"), name="static")

UPLOADS_DIR = "uploads"
os.makedirs(UPLOADS_DIR, exist_ok=True)


# -------------------------
# MiniApp
# -------------------------
@app.get("/", response_class=HTMLResponse)
def index():
    return FileResponse("web/kling.html")


# -------------------------
# Раздача загруженных картинок (чтобы Kling мог скачать по URL)
# -------------------------
@app.get("/uploads/{filename}")
def get_upload(filename: str):
    path = os.path.join(UPLOADS_DIR, filename)
    return FileResponse(path)


# -------------------------
# Telegram webhook endpoint
# -------------------------
@app.post("/telegram/webhook")
async def telegram_webhook(req: Request):
    update_json = await req.json()
    from telebot.types import Update
    update = Update.de_json(update_json)
    bot.process_new_updates([update])
    return {"ok": True}


# -------------------------
# Auto set webhook on startup (Render)
# -------------------------
@app.on_event("startup")
async def on_startup():
    base = (TELEGRAM_WEBHOOK_BASE or "").rstrip("/")
    if not base:
        print("⚠️ TELEGRAM_WEBHOOK_BASE not set -> webhook NOT configured automatically.")
        return

    webhook_url = f"{base}/telegram/webhook"

    try:
        bot.remove_webhook()
    except Exception:
        pass

    ok = bot.set_webhook(url=webhook_url)
    print(f"✅ Webhook set: {webhook_url} | result={ok}")


# -------------------------
# Telegram WebApp initData verify
# -------------------------
def verify_init_data(init_data: str, bot_token: str) -> dict:
    parsed = dict(urllib.parse.parse_qsl(init_data, keep_blank_values=True))
    if "hash" not in parsed:
        raise Exception("initData hash missing")

    received_hash = parsed.pop("hash")

    data_check_string = "\n".join([f"{k}={v}" for k, v in sorted(parsed.items())])

    secret_key = hmac.new(
        key=b"WebAppData",
        msg=bot_token.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).digest()

    calculated_hash = hmac.new(
        key=secret_key,
        msg=data_check_string.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).hexdigest()

    if calculated_hash != received_hash:
        raise Exception("initData hash invalid")

    return parsed


def tg_send_message(chat_id: int, text: str):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    r = requests.post(url, data={"chat_id": chat_id, "text": text}, timeout=30)
    if r.status_code != 200:
        raise Exception(f"sendMessage failed: {r.status_code} {r.text}")


def tg_send_video(chat_id: int, video_url: str, caption: str):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendVideo"
    r = requests.post(
        url,
        data={"chat_id": chat_id, "video": video_url, "caption": caption},
        timeout=60,
    )
    if r.status_code != 200:
        raise Exception(f"sendVideo failed: {r.status_code} {r.text}")


# -------------------------
# Реальный backend для MiniApp -> Kling -> видео в чат
# -------------------------
@app.post("/api/kling_effect")
async def kling_effect(request: Request):
    form = await request.form()

    init_data = form.get("initData")
    effect_id = form.get("effect_id", "default")
    prompt = (form.get("prompt", "") or "").strip() or "Make it magical"

    photo = form.get("photo")
    if not init_data:
        return JSONResponse({"ok": False, "error": "initData missing"}, status_code=400)
    if not photo:
        return JSONResponse({"ok": False, "error": "photo missing"}, status_code=400)

    # 1) verify Telegram initData -> get user id (we use it as chat_id for private chat)
    try:
        parsed = verify_init_data(str(init_data), TELEGRAM_TOKEN)
        user_obj = json.loads(parsed.get("user", "{}"))
        chat_id = int(user_obj["id"])
    except Exception as e:
        return JSONResponse({"ok": False, "error": f"auth failed: {e}"}, status_code=403)

    # 2) Save file
    filename = f"{int(time.time())}_{chat_id}.jpg"
    file_path = os.path.join(UPLOADS_DIR, filename)
    with open(file_path, "wb") as f:
        shutil.copyfileobj(photo.file, f)

    # 3) Build URL for Kling to fetch
    base = (TELEGRAM_WEBHOOK_BASE or "").rstrip("/")
    if not base:
        return JSONResponse({"ok": False, "error": "TELEGRAM_WEBHOOK_BASE not set"}, status_code=500)

    image_url = f"{base}/uploads/{filename}"

    # 4) Start Kling and notify user
    try:
        tg_send_message(chat_id, "✅ Фото получил. Начинаю колдовать видео ✨")

        task_id = create_kling_image_to_video(
            prompt=f"[{effect_id}] {prompt}",
            image_url=image_url,
            model_name="kling-v2-5-turbo",
            mode="pro",
            duration=5,
            cfg_scale=0.5,
        )

        video_url = poll_kling_result(task_id, max_attempts=60, delay=5)

        tg_send_video(
            chat_id,
            video_url,
            f"🎬 Готово! Вот твоё видео ✨\nПолное качество: {video_url}",
        )

        return JSONResponse({"ok": True})

    except Exception as e:
        try:
            tg_send_message(chat_id, f"Что-то пошло не так 😔\n{e}")
        except Exception:
            pass
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)