# services/image_utils.py
#
# Вспомогательная функция, которая умеет доставать file_id
# и из обычного фото (photo), и из документа-картинки (document).

from telebot import types


def extract_image_file_id(message: types.Message) -> str | None:
    """
    Возвращает file_id картинки, если в message есть:
    - photo
    - document, у которого mime_type image/* или подходящее расширение.

    Если картинки нет — возвращает None.
    """
    # 1) Сначала проверяем обычное фото
    if message.photo:
        return message.photo[-1].file_id

    # 2) Проверяем документ
    if message.content_type == "document":
        doc = message.document
        if not doc:
            return None

        mime = (doc.mime_type or "").lower()
        name = (doc.file_name or "").lower()

        if mime.startswith("image/"):
            return doc.file_id

        for ext in (".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif"):
            if name.endswith(ext):
                return doc.file_id

    return None
