# services/nanobanana_service.py
#
# Работа с NanoBanana PRO: /generate-pro + /record-info
# По умолчанию: 2K, aspect 1:1
# Поддержка:
#   - TEXT -> IMAGE
#   - IMAGE -> IMAGE (одно фото)
#   - MULTI-IMAGE Remix -> общая сцена из нескольких фото
#   - возврат bytes + оригинальный resultImageUrl

import time
import requests
from config import NANOBANANA_API_KEY, NANOBANANA_BASE_URL, NANOBANANA_MODEL


# =============================================================
# Базовые настройки
# =============================================================

if not NANOBANANA_BASE_URL.endswith("/"):
    BASE_URL = NANOBANANA_BASE_URL
else:
    BASE_URL = NANOBANANA_BASE_URL.rstrip("/")

GENERATE_PRO_URL = f"{BASE_URL}/generate-pro"
RECORD_INFO_URL = f"{BASE_URL}/record-info"

HEADERS_JSON = {
    "Authorization": f"Bearer {NANOBANANA_API_KEY}",
    "Content-Type": "application/json",
}


def _ensure_pro_model():
    """
    На всякий случай подсвечиваем, если модель в конфиге не PRO.
    """
    if NANOBANANA_MODEL != "nano-banana-pro":
        print(
            f"[NanoBanana] ВНИМАНИЕ: NANOBANANA_MODEL={NANOBANANA_MODEL}, "
            f"но используется PRO-эндпоинт /generate-pro."
        )


# =============================================================
# Создание задач
# =============================================================

def create_pro_text_task(
    prompt: str,
    resolution: str = "2K",
    aspect: str = "1:1",
) -> str:
    """
    TEXT -> IMAGE.
    resolution: "1K" / "2K" / "4K"
    aspect: "1:1" / "16:9" / "9:16" / "3:4" / ...
    """
    _ensure_pro_model()

    payload = {
        "prompt": prompt,
        "resolution": resolution,
        "aspectRatio": aspect,
        "callBackUrl": "https://example.com/callback",
    }

    resp = requests.post(
        GENERATE_PRO_URL,
        headers=HEADERS_JSON,
        json=payload,
        timeout=90,
    )

    try:
        data = resp.json()
    except Exception:
        raise Exception(f"NanoBanana PRO: не удалось разобрать ответ: {resp.text}")

    if resp.status_code != 200 or data.get("code") != 200:
        msg = data.get("msg") or data.get("message") or resp.text
        raise Exception(f"NanoBanana PRO ошибка: {msg}")

    task_id = (data.get("data") or {}).get("taskId")
    if not task_id:
        raise Exception(f"NanoBanana PRO не вернул taskId: {data}")

    return task_id


def create_pro_image_task(
    prompt: str,
    image_url: str,
    resolution: str = "2K",
    aspect: str = "1:1",
) -> str:
    """
    IMAGE -> IMAGE (одно фото).
    """
    _ensure_pro_model()

    payload = {
        "prompt": prompt,
        "imageUrls": [image_url],
        "resolution": resolution,
        "aspectRatio": aspect,
        "callBackUrl": "https://example.com/callback",
    }

    resp = requests.post(
        GENERATE_PRO_URL,
        headers=HEADERS_JSON,
        json=payload,
        timeout=90,
    )

    try:
        data = resp.json()
    except Exception:
        raise Exception(f"NanoBanana PRO (image): не удалось разобрать ответ: {resp.text}")

    if resp.status_code != 200 or data.get("code") != 200:
        msg = data.get("msg") or data.get("message") or resp.text
        raise Exception(f"NanoBanana PRO (image) ошибка: {msg}")

    task_id = (data.get("data") or {}).get("taskId")
    if not task_id:
        raise Exception("NanoBanana PRO image: taskId не найден")

    return task_id


def create_pro_multi_image_task(
    prompt: str,
    image_urls,
    resolution: str = "2K",
    aspect: str = "1:1",
) -> str:
    """
    MULTI-IMAGE Remix: общая сцена из нескольких изображений.
    image_urls: список URL исходных картинок.
    """
    _ensure_pro_model()

    payload = {
        "prompt": prompt,
        "imageUrls": image_urls,
        "resolution": resolution,
        "aspectRatio": aspect,
        "callBackUrl": "https://example.com/callback",
    }

    resp = requests.post(
        GENERATE_PRO_URL,
        headers=HEADERS_JSON,
        json=payload,
        timeout=90,
    )

    try:
        data = resp.json()
    except Exception:
        raise Exception(f"NanoBanana PRO (multi): не удалось разобрать ответ: {resp.text}")

    if resp.status_code != 200 or data.get("code") != 200:
        msg = data.get("msg") or data.get("message") or resp.text
        raise Exception(f"NanoBanana PRO (multi) ошибка: {msg}")

    task_id = (data.get("data") or {}).get("taskId")
    if not task_id:
        raise Exception("NanoBanana PRO multi: taskId не найден")

    return task_id


# =============================================================
# Опрос задачи
# =============================================================

def poll_task(task_id: str, timeout: int = 240):
    """
    Ожидаем завершения задачи.
    timeout — общий лимит ожидания (сек).
    """
    start = time.time()

    while True:
        resp = requests.get(
            RECORD_INFO_URL,
            headers={"Authorization": f"Bearer {NANOBANANA_API_KEY}"},
            params={"taskId": task_id},
            timeout=60,
        )

        try:
            body = resp.json()
        except Exception:
            raise Exception(f"NanoBanana PRO record-info: не удалось разобрать ответ: {resp.text}")

        if resp.status_code != 200 or body.get("code") != 200:
            msg = body.get("msg") or body.get("message") or resp.text
            raise Exception(f"NanoBanana PRO record-info ошибка: {msg}")

        data = body.get("data") or {}
        flag = data.get("successFlag")

        # 0 = generating, 1 = success, 2/3 = failed
        if flag == 1:
            return "success", data
        elif flag in (2, 3):
            return "failed", data

        if time.time() - start > timeout:
            raise Exception("NanoBanana PRO timeout")

        time.sleep(2)


# =============================================================
# Вспомогательные функции для результата
# =============================================================

def _extract_result_url(data: dict) -> str:
    """
    Достаёт resultImageUrl из ответа.
    """
    response_block = data.get("response") or {}
    url = response_block.get("resultImageUrl")
    if not url:
        raise Exception(f"NanoBanana PRO: нет resultImageUrl: {data}")
    return url


def _download_result_bytes(url: str) -> bytes:
    """
    Скачивает картинку по URL и возвращает байты.
    """
    img = requests.get(url, timeout=90)
    if img.status_code != 200:
        raise Exception(f"NanoBanana PRO: не удалось скачать картинку: {img.status_code}")
    return img.content


# =============================================================
# Публичный API: TEXT → IMAGE
# =============================================================

def generate_image(
    prompt: str,
    resolution: str = "2K",
    aspect: str = "1:1",
    return_url: bool = False,
):
    """
    Генерация по текстовому описанию.
    По умолчанию: 2K, 1:1.
    return_url:
      False → вернуть только байты
      True  → вернуть (байты, url)
    """

    print(f"[NanoBanana] generate_image(prompt=..., resolution={resolution}, aspect={aspect})")

    task_id = create_pro_text_task(prompt, resolution=resolution, aspect=aspect)
    status, data = poll_task(task_id)

    if status != "success":
        raise Exception(data.get("errorMessage") or "Ошибка генерации")

    url = _extract_result_url(data)
    img_bytes = _download_result_bytes(url)

    if return_url:
        return img_bytes, url
    return img_bytes


# =============================================================
# Публичный API: IMAGE → IMAGE (одно фото)
# =============================================================

def generate_image_from_url(
    image_url: str,
    prompt: str,
    resolution: str = "2K",
    aspect: str = "1:1",
    return_url: bool = False,
):
    """
    Редактирование по URL исходного изображения.
    По умолчанию: 2K, 1:1.
    """

    print(f"[NanoBanana] generate_image_from_url(prompt=..., resolution={resolution}, aspect={aspect})")

    task_id = create_pro_image_task(
        prompt=prompt,
        image_url=image_url,
        resolution=resolution,
        aspect=aspect,
    )
    status, data = poll_task(task_id)

    if status != "success":
        raise Exception(data.get("errorMessage") or "Ошибка обработки изображения")

    url = _extract_result_url(data)
    img_bytes = _download_result_bytes(url)

    if return_url:
        return img_bytes, url
    return img_bytes


# =============================================================
# Публичный API: MULTI-IMAGE Remix → общая сцена
# =============================================================

def generate_scene_from_urls(
    image_urls,
    prompt: str,
    resolution: str = "2K",
    aspect: str = "1:1",
    return_url: bool = False,
):
    """
    MULTI-IMAGE Remix: создаёт одну общую сцену из нескольких фото.
    image_urls: список URL исходных изображений.
    """

    print(
        f"[NanoBanana] generate_scene_from_urls(num_images={len(image_urls)}, "
        f"resolution={resolution}, aspect={aspect})"
    )

    task_id = create_pro_multi_image_task(
        prompt=prompt,
        image_urls=image_urls,
        resolution=resolution,
        aspect=aspect,
    )
    status, data = poll_task(task_id)

    if status != "success":
        raise Exception(data.get("errorMessage") or "Ошибка мульти-сцены")

    url = _extract_result_url(data)
    img_bytes = _download_result_bytes(url)

    if return_url:
        return img_bytes, url
    return img_bytes


# =============================================================
# Для фонового воркера
# =============================================================

def check_generation_task(task_id: str):
    """
    Для фонового воркера.
    Возвращает:
    {
      "done": bool,
      "success": bool,
      "image_bytes": bytes | None,
      "image_url": str | None,
      "error": str | None,
    }
    """
    status, data = poll_task(task_id, timeout=10)

    if status == "success":
        try:
            url = _extract_result_url(data)
            img = _download_result_bytes(url)
        except Exception as e:
            return {
                "done": True,
                "success": False,
                "image_bytes": None,
                "image_url": None,
                "error": str(e),
            }

        return {
            "done": True,
            "success": True,
            "image_bytes": img,
            "image_url": url,
            "error": None,
        }

    if status == "failed":
        return {
            "done": True,
            "success": False,
            "image_bytes": None,
            "image_url": None,
            "error": data.get("errorMessage") or "NanoBanana PRO ошибка",
        }

    return {
        "done": False,
        "success": False,
        "image_bytes": None,
        "image_url": None,
        "error": None,
    }