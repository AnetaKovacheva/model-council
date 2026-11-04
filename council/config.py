"""Panel + chairman configuration. Edit this file (or env vars) to change who sits on the council."""
import os
from dataclasses import dataclass


@dataclass(frozen=True)
class ModelSpec:
    name: str        # display name shown in the UI
    provider: str    # "anthropic" | "openai" | "google_genai"
    model: str       # provider model ID
    role_hint: str = ""


# NOTE: verify OpenAI / Gemini IDs against each provider's current model list.
PANEL: list[ModelSpec] = [
    ModelSpec(
        "Claude", "anthropic",
        os.getenv("COUNCIL_CLAUDE_MODEL", "claude-sonnet-5-5"),
        "Surface uncertainty, hidden assumptions and edge cases.",
    ),
    ModelSpec(
        "GPT", "openai",
        os.getenv("COUNCIL_OPENAI_MODEL", "gpt-5"),
        "Prioritise rigorous logical structure and step-by-step derivations.",
    ),
    ModelSpec(
        "Gemini", "google_genai",
        os.getenv("COUNCIL_GEMINI_MODEL", "gemini-3.6-flash"),
        "Prioritise breadth, context and real-world grounding.",
    ),
]

# Use your strongest model here; synthesis quality matters most.
CHAIRMAN = ModelSpec(
    "Chairman", "anthropic",
    os.getenv("COUNCIL_CHAIRMAN_MODEL", "claude-opus-5-5"),
)
