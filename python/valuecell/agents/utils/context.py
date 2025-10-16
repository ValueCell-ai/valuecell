from typing import Any, Dict, Optional

from valuecell.core.constants import LANGUAGE, TIMEZONE


def build_ctx_from_dep(
    dep: Optional[Dict[str, Any]],
) -> Dict[str, str] | None:
    if not dep:
        return None

    context = {}
    lang_ctx = _build_lang_ctx_from_dep(dep)
    if lang_ctx:
        context["compose_answer_hint"] = lang_ctx

    return context


def _build_lang_ctx_from_dep(
    dependencies: Optional[Dict[str, Any]],
) -> str | None:
    if not dependencies:
        return None

    user_lang = dependencies.get(LANGUAGE)
    user_tz = dependencies.get(TIMEZONE)

    parts = []
    parts.append(
        "When composing your answer, consider the user's language and timezone:"
    )
    if user_lang:
        parts.append(f"- Preferred language: {user_lang}")
    else:
        parts.append(
            "- Preferred language: not set. Infer the user's language from their query and respond in that language."
        )

    if user_tz:
        parts.append(
            f"- Timezone: {user_tz} (use this to interpret or present times/dates)"
        )
    else:
        parts.append(
            "- Timezone: not set. Do NOT ask the user for their timezone unless absolutely necessary. Instead, infer timezone from context (locale, timestamps, phrasing) when possible; if you cannot reasonably infer it, default to UTC when presenting absolute times."
        )

    return "\n".join(parts)
