import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.settings_service import SettingsService

class AiError(Exception):
    pass

async def ask_ai(session: AsyncSession, prompt: str) -> tuple[str, int, str]:
    svc = SettingsService(session)
    api_key = await svc.get("ai_api_key")
    if not api_key:
        raise AiError("AI API key не настроен в админке")

    base_url = (await svc.get("ai_base_url")).rstrip("/")
    model = await svc.get("ai_model")
    system_prompt = await svc.get("ai_system_prompt")
    max_tokens = await svc.get_int("ai_max_tokens", 1000)
    temperature = await svc.get_float("ai_temperature", 0.7)
    timeout = await svc.get_int("ai_timeout", 60)

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ],
        "max_tokens": max_tokens,
        "temperature": temperature,
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                f"{base_url}/chat/completions", json=payload, headers=headers
            )
    except httpx.HTTPError as exc:
        raise AiError(f"Сетевая ошибка: {exc}") from exc

    if response.status_code >= 400:
        raise AiError(f"AI API {response.status_code}: {response.text[:300]}")

    data = response.json()
    try:
        answer = data["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError) as exc:
        raise AiError("Неожиданный формат ответа AI API") from exc

    tokens = int(data.get("usage", {}).get("total_tokens", 0) or 0)
    return answer, tokens, model

async def check_ai_connection(session: AsyncSession) -> tuple[bool, str]:
    try:
        answer, _, model = await ask_ai(session, "Ответь одним словом: ок")
        return True, f"{model}: {answer[:80]}"
    except AiError as exc:
        return False, str(exc)
