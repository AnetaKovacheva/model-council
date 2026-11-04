# Model Council 🏛️

A multi-model AI agent council: several LLMs answer the same question independently, review each other's answers blind, and a chairman model synthesizes the final result with a confidence signal.

Built with Python, LangGraph/LangChain and Streamlit. The concept follows [this MindStudio article](https://www.mindstudio.ai/blog/multi-model-ai-agent-council).

## How it works

```
question ─→ independent drafts (Claude, GPT, Gemini, in parallel)
         ─→ anonymize & shuffle responses
         ─→ blind peer review (each model scores the others, never its own)
         ─→ chairman synthesis (final answer, agreements, disagreements, confidence)
```

The Streamlit UI shows live progress, the final answer with a confidence badge, the independent drafts (authors revealed afterwards), peer-review scores, and an optional single-model baseline for comparison.

## Setup

```bash
poetry install
cp .env.example .env    # add your API keys
poetry run streamlit run app.py
```

Required keys in `.env`: `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `GOOGLE_API_KEY`.

## Configuration

Panel and chairman models are defined in `council/config.py` and can be overridden in `.env`:

```
COUNCIL_CLAUDE_MODEL=
COUNCIL_OPENAI_MODEL=
COUNCIL_GEMINI_MODEL=
COUNCIL_CHAIRMAN_MODEL=
```

Model availability and quotas change often, so check each provider's current model list. Some models (for example Gemini Pro) may require a paid tier.

## Project structure

```
app.py              Streamlit UI
council/
  config.py         panel and chairman models
  graph.py          LangGraph pipeline
  prompts.py        panelist, reviewer and chairman prompts
  schemas.py        structured-output schemas
  models.py         model factory helpers
scripts/
  list_gemini_models.py   list Gemini models available to your key
```

## When to use it

Councils help on ambiguous, multi-step or high-stakes questions. For simple factual queries a single model is cheaper and faster. A full run makes about 7 LLM calls.
