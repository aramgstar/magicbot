from openai import OpenAI
from config import OPENAI_API_KEY

client = OpenAI(api_key=OPENAI_API_KEY)


def build_prompt(session: dict) -> str:
    """
    Делает красивый промпт через ChatGPT.
    """

    what = session.get("what", "")
    for_whom = session.get("for_whom", "")
    mood = session.get("mood", "")

    system_prompt = (
        "Ты — дизайнер, создающий красивый короткий промпт "
        "для генерации картинки. Аудитория — взрослые женщины, "
        "домохозяйки. Верни ТОЛЬКО промпт на английском."
    )

    user_prompt = (
        f"What: {what}\n"
        f"For: {for_whom}\n"
        f"Mood: {mood}\n"
        f"Create one beautiful descriptive prompt."
    )

    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.7,
    )

    return response.choices[0].message.content.strip()
