import os

from agno.models.google import Gemini
from agno.models.openrouter import OpenRouter


def get_model(env_key: str):
    model_id = os.getenv(env_key)
    if os.getenv("GOOGLE_API_KEY"):
        return Gemini(id=model_id or "gemini-2.5-flash")
    return OpenRouter(id=model_id or "google/gemini-2.5-flash", max_tokens=None)
