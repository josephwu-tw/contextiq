from .base import BaseLLMClient
from .gemini import GeminiClient
from .claude import ClaudeClient
from .openai import OpenAIClient

_REGISTRY = [
    ("Gemini", GeminiClient),
    ("Claude", ClaudeClient),
    ("ChatGPT", OpenAIClient),
]


def load_available_clients() -> dict[str, BaseLLMClient]:
    """
    Tries to instantiate each provider. Returns only those whose API key
    is present in the environment, so callers never need to handle RuntimeError.
    """
    available = {}
    for name, cls in _REGISTRY:
        try:
            available[name] = cls()
        except RuntimeError:
            pass
    return available
