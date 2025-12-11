import time
import requests
import uvicorn
import jwt  # pip install PyJWT
from fastapi import FastAPI, Form
from fastapi.middleware.cors import CORSMiddleware

# ===========================
# KLING KEYS (ТВОИ)
# ===========================
AK = "AgJFMHtbQTrKg9MT4JTLRd939kabpGeM"
SK = "88gJQ8r39ppLLCgtPrbNM8NpTJGCJMMB"

# ===========================
# KLING endpoints
# ===========================
BASE = "https://api-singapore.klingai.com/v1"
KLING_EFFECTS_URL = f"{BASE}/videos/effects"      # создание задачи
KLING_TASK_URL = f"{BASE}/videos/effects"        # проверка статуса

# ===========================
# FastAPI app
# ===========================
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],      # для локального теста
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# демо-картинки для эффектов Kling (официальные URL)
DEMO_IMAGES = {
    "snowglobe": "https://v15-kling.klingai.com/kos/s101/nlav112372/kling-op/effects_pic/snowglobe.jpeg",
    "firework_2026": "https://v15-kling.klingai.com/kos/s101/nlav112372/kling-op/effects_pic/firework_2026.jpeg",
    "glamour_photo_shoot": "https://v15-kling.klingai.com/kos/s101/nlav112372/kling-op/effects_pic/glamour_photo_shoot.jpeg",
    "box_of_joy": "https://v15-kling.klingai.com/kos/s101/nlav112372/kling-op/effects_pic/box_of_joy.jpeg",
}


def generate_kling_jwt(ak: str, sk: str) -> str:
    """JWT как в официальном примере Kling"""
    headers = {"alg": "HS256", "typ": "JWT"}
    now = int(time.time())
    payload = {
        "iss": ak,
        "exp": now + 1800,
        "nbf": now - 5,
    }
    token = jwt.encode(payload, sk, algorithm="HS256", headers=headers)
    if isinstance(token, bytes):
        token = token.decode("utf-8")
    return token


@app.post("/api/kling_effect")
async def kling_effect(
    effect_id: str = Form(...),
    image_url: str = Form(None),   # 👈 сюда придёт URL фотки из бота, если отправим
):
    """
    Создаём задачу Kling по effect_scene.
    Если передан image_url — используем его.
    Если нет — подставляем демо-картинку.
    """
    api_token = generate_kling_jwt(AK, SK)

    if image_url and image_url.strip():
        img = image_url.strip()
    else:
        img = DEMO_IMAGES.get(effect_id, DEMO_IMAGES["snowglobe"])

    payload = {
        "effect_scene": effect_id,
        "input": {
            "image": img,
            "duration": "5"
        }
    }

    headers = {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json",
    }

    resp = requests.post(KLING_EFFECTS_URL, json=payload, headers=headers, timeout=60)

    if not resp.ok:
        return {
            "ok": False,
            "status_code": resp.status_code,
            "text": resp.text,
            "image_used": img,
        }

    return {
        "ok": True,
        "image_used": img,
        "kling_raw": resp.json(),
    }


@app.get("/api/kling_task_status")
def kling_task_status(task_id: str):
    """
    Проверяем статус эффекта:
    GET /v1/videos/effects/{task_id}
    """
    api_token = generate_kling_jwt(AK, SK)

    headers = {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json",
    }

    url = f"{KLING_TASK_URL}/{task_id}"

    resp = requests.get(url, headers=headers, timeout=30)

    if not resp.ok:
        return {
            "ok": False,
            "status_code": resp.status_code,
            "text": resp.text,
        }

    return {
        "ok": True,
        "kling_raw": resp.json(),
    }


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
