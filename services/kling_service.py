# services/kling_service.py
#
# Работа с официальным Kling API (JWT авторизация).
# Используем модель:
#     kling-v2-5-turbo   ← проверенная тобой
#
# Если захочешь сменить модель, просто пропиши:
#     KLING_IMAGE_MODEL=xxx
# в .env — сервис сам её подхватит.

import os
import time
import jwt
import requests
from dotenv import load_dotenv

load_dotenv()

AK = os.getenv("KLING_ACCESS_KEY")
SK = os.getenv("KLING_SECRET_KEY")
BASE_URL = os.getenv("KLING_API_BASE_URL", "https://api.klingai.com").rstrip("/")

# Модель по умолчанию устанавливаем здесь.
DEFAULT_IMAGE_MODEL = os.getenv("KLING_IMAGE_MODEL", "kling-v2-5-turbo")


def _make_jwt_token() -> str:
    """
    Генерирует JWT токен для Kling API.
    """
    if not AK or not SK:
        raise RuntimeError("❌ Нет KLING_ACCESS_KEY или KLING_SECRET_KEY в .env")

    now = int(time.time())

    payload = {
        "iss": AK,
        "exp": now + 1800,
        "nbf": now - 5,
    }

    token = jwt.encode(payload, SK, algorithm="HS256")
    if isinstance(token, bytes):
        token = token.decode("utf-8")
    return token


def _headers():
    return {
        "Authorization": f"Bearer {_make_jwt_token()}",
        "Content-Type": "application/json",
    }


# ------------------------------------------------------------
#  Создание задачи IMAGE → VIDEO
# ------------------------------------------------------------

def create_kling_image_to_video(
    prompt: str,
    image_url: str,
    model_name: str | None = None,
    mode: str = "pro",
    duration: int = 5,
    cfg_scale: float = 0.5,
) -> str:
    """
    Создаёт задачу анимации изображения на Kling.
    """
    url = f"{BASE_URL}/v1/videos/image2video"

    model_to_use = model_name or DEFAULT_IMAGE_MODEL

    payload = {
        "prompt": prompt,
        "image": image_url,
        "model_name": model_to_use,
        "mode": mode,
        "duration": str(duration),
        "cfg_scale": cfg_scale,
    }

    resp = requests.post(url, headers=_headers(), json=payload, timeout=60)

    if resp.status_code != 200:
        raise RuntimeError(f"Kling create error: {resp.status_code} {resp.text}")

    data = resp.json()

    task_id = (
        data.get("task_id")
        or data.get("data", {}).get("task_id")
        or data.get("taskId")
        or data.get("data", {}).get("taskId")
    )

    if not task_id:
        raise RuntimeError(f"Kling response error: task_id not found. Raw: {data}")

    return task_id


# ------------------------------------------------------------
#  Получение статуса задачи
# ------------------------------------------------------------

def get_kling_task_status(task_id: str) -> tuple[str, str | None]:
    """
    Возвращает (status, video_url).
    status:
        submitted  – в очереди
        processing / running – в процессе
        succeed / completed – готово
        failed – ошибка
    """
    img_url = f"{BASE_URL}/v1/videos/image2video/{task_id}"
    txt_url = f"{BASE_URL}/v1/videos/text2video/{task_id}"

    for endpoint in (img_url, txt_url):
        resp = requests.get(endpoint, headers=_headers(), timeout=60)

        if resp.status_code == 404:
            continue

        if resp.status_code != 200:
            raise RuntimeError(f"Kling status error: {resp.status_code} {resp.text}")

        data = resp.json()

        status = (
            data.get("status")
            or data.get("task_status")
            or data.get("data", {}).get("status")
            or data.get("data", {}).get("task_status")
            or "unknown"
        )

        # Ссылка на видео
        result = (
            data.get("task_result")
            or data.get("data", {}).get("task_result")
            or data.get("data")
        )

        video_url = None

        if isinstance(result, dict):
            arr = result.get("videos") or result.get("video")
            if isinstance(arr, list) and arr:
                first = arr[0]
                if isinstance(first, dict):
                    video_url = first.get("url") or first.get("video_url")
                elif isinstance(first, str):
                    video_url = first
            if not video_url:
                video_url = result.get("video_url") or result.get("videoUrl")

        return status.lower(), video_url

    raise RuntimeError("Kling: cannot get status from any endpoint")


# ------------------------------------------------------------
#  Блокирующий режим (не используется напрямую в боте)
# ------------------------------------------------------------

def poll_kling_result(task_id: str, max_attempts=30, delay=5) -> str:
    for attempt in range(1, max_attempts + 1):
        status, video_url = get_kling_task_status(task_id)
        print(f"[Kling] poll {attempt}: {status}")

        if status in ("succeed", "success", "completed"):
            if not video_url:
                raise RuntimeError("Status success but video_url is missing")
            return video_url

        if status in ("failed", "error"):
            raise RuntimeError("Kling task failed")

        time.sleep(delay)

    raise RuntimeError("Kling poll timeout")