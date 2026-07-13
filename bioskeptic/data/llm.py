from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()                              # ANTHROPIC_API_KEY from .env (SDK reads it from the environment)
_client = Anthropic()
_MODEL = "claude-opus-4-8"
_CACHE: dict = {}                          # memoize by prompt so a run is stable + cheap


# Ask Claude a one-shot question and return its plain-text answer (used for fuzzy semantic judgments
# a database can't answer, e.g. "which of these tissues is this disease in?"). Cached; abstains on error.
def ask_claude(prompt: str, max_tokens: int = 300) -> str | None:
    if prompt in _CACHE:
        return _CACHE[prompt]
    try:
        msg = _client.messages.create(model=_MODEL, max_tokens=max_tokens,
                                       messages=[{"role": "user", "content": prompt}])
        text = "".join(b.text for b in msg.content if getattr(b, "type", None) == "text").strip()
    except Exception:
        return None
    _CACHE[prompt] = text
    return text
