from functools import lru_cache

from langchain.chat_models import init_chat_model
from langchain_core.language_models import BaseChatModel

from .config import ModelSpec


@lru_cache(maxsize=None)
def get_model(spec: ModelSpec) -> BaseChatModel:
    # Temperature is deliberately not set: some newer models reject custom values.
    return init_chat_model(spec.model, model_provider=spec.provider)


def to_text(message) -> str:
    """Providers return either a str or a list of content blocks; normalise to str."""
    content = message.content
    if isinstance(content, str):
        return content
    parts = []
    for block in content:
        if isinstance(block, str):
            parts.append(block)
        elif isinstance(block, dict) and block.get("type", "text") == "text":
            parts.append(block.get("text", ""))
    return "".join(parts)

def structured(spec: ModelSpec, schema):
    """Structured-output runnable; Anthropic needs json_schema on the 5.x models."""
    model = get_model(spec)
    if spec.provider == "anthropic":
        return model.with_structured_output(schema, method="json_schema")
    return model.with_structured_output(schema)
