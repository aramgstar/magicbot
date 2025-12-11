# utils/tasks.py

import uuid

# Готовые изображения, к которым привязана кнопка "Анимировать"
_animation_tasks = {}  # task_id -> {prompt, image_bytes, user_id}

# Висящие в генерации NanoBanana задачи
_pending_generations = {}  # nb_task_id -> {user_id, chat_id, prompt, model}


# --------- Для анимации (готовые картинки) ---------

def create_task(prompt, image_bytes, user_id):
    """
    Создаёт задачу для дальнейшей анимации.
    Возвращает внутренний task_id, который уходит в callback "animate:<task_id>".
    """
    task_id = str(uuid.uuid4())
    _animation_tasks[task_id] = {
        "prompt": prompt,
        "image_bytes": image_bytes,
        "user_id": user_id,
    }
    return task_id


def get_task(task_id):
    """
    Возвращает задачу по task_id или None.
    """
    return _animation_tasks.get(task_id)


# --------- Для очереди NanoBanana (без ожидания) ---------

def add_pending_generation(nb_task_id: str, user_id: int, chat_id: int, prompt: str, model: str):
    """
    Регистрирует задачу, которая сейчас генерится на стороне NanoBanana.
    """
    _pending_generations[nb_task_id] = {
        "user_id": user_id,
        "chat_id": chat_id,
        "prompt": prompt,
        "model": model,
    }


def get_all_pending_generations():
    """
    Возвращает список всех задач в очереди в виде удобного списка словарей.
    """
    result = []
    for nb_task_id, info in _pending_generations.items():
        item = {"nb_task_id": nb_task_id}
        item.update(info)
        result.append(item)
    return result


def remove_pending_generation(nb_task_id: str):
    """
    Удаляет задачу из очереди ожидания по её NanoBanana taskId.
    """
    _pending_generations.pop(nb_task_id, None)
