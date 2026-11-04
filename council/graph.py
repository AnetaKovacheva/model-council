"""LangGraph pipeline:

START ─fan-out→ draft (x N, parallel) → anonymize ─fan-out→ review (x N, parallel) → chairman → END
"""
import operator
import random
import time
from typing import Annotated, TypedDict

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from langgraph.types import Send

from .config import CHAIRMAN, PANEL
from .models import get_model, structured, to_text
from .prompts import CHAIRMAN_SYSTEM, PANELIST_SYSTEM, REVIEW_SYSTEM
from .schemas import FinalAnswer, ReviewBatch

LABELS = "ABCDEFGH"
SPECS = {p.name: p for p in PANEL}


class CouncilState(TypedDict, total=False):
    question: str
    drafts: Annotated[list[dict], operator.add]    # {"model", "text", "seconds"}
    responses: dict[str, str]                      # "Response A" -> text
    label_to_model: dict[str, str]                 # "Response A" -> "Claude"
    reviews: Annotated[list[dict], operator.add]   # Review fields + "reviewer"
    final: dict
    errors: Annotated[list[str], operator.add]


# ---- Layer 1: independent sampling -------------------------------------------------
def dispatch_drafts(state: CouncilState):
    return [Send("draft", {"question": state["question"], "panelist": p.name}) for p in PANEL]


def draft(payload: dict):
    spec = SPECS[payload["panelist"]]
    t0 = time.perf_counter()
    try:
        msg = get_model(spec).invoke([
            SystemMessage(PANELIST_SYSTEM.format(role_hint=spec.role_hint)),
            HumanMessage(payload["question"]),
        ])
        return {"drafts": [{
            "model": spec.name,
            "text": to_text(msg),
            "seconds": round(time.perf_counter() - t0, 1),
        }]}
    except Exception as e:  # keep the council going if one provider fails
        return {"errors": [f"{spec.name} draft failed: {e}"]}


# ---- Layer 2: blind peer review ----------------------------------------------------
def anonymize(state: CouncilState):
    drafts = list(state.get("drafts", []))
    if len(drafts) < 2:
        raise ValueError(f"Need at least 2 successful drafts, got {len(drafts)}. Errors: {state.get('errors')}")
    random.shuffle(drafts)  # label order must not leak panel order
    responses, mapping = {}, {}
    for i, d in enumerate(drafts):
        label = f"Response {LABELS[i]}"
        responses[label] = d["text"]
        mapping[label] = d["model"]
    return {"responses": responses, "label_to_model": mapping}


def dispatch_reviews(state: CouncilState):
    mapping = state["label_to_model"]
    drafted = set(mapping.values())
    sends = []
    for p in PANEL:
        if p.name not in drafted:
            continue
        # A model never reviews its own answer (avoids self-preference bias).
        others = {l: t for l, t in state["responses"].items() if mapping[l] != p.name}
        sends.append(Send("review", {"question": state["question"], "reviewer": p.name, "to_review": others}))
    return sends


def review(payload: dict):
    spec = SPECS[payload["reviewer"]]
    block = "\n\n".join(f"### {label}\n{text}" for label, text in payload["to_review"].items())
    try:
        # out: ReviewBatch = get_model(spec).with_structured_output(ReviewBatch).invoke([
        out: ReviewBatch = structured(spec, ReviewBatch).invoke([
            SystemMessage(REVIEW_SYSTEM),
            HumanMessage(f"Question:\n{payload['question']}\n\nResponses to review:\n\n{block}"),
        ])
        recs = []
        for r in out.reviews:
            d = r.model_dump()
            for k in ("accuracy", "completeness", "reasoning"):
                d[k] = max(1, min(5, int(d[k])))
            d["reviewer"] = spec.name
            recs.append(d)
        return {"reviews": recs}
    except Exception as e:
        return {"errors": [f"{spec.name} review failed: {e}"]}


# ---- Layer 3: chairman -------------------------------------------------------------
def chairman(state: CouncilState):
    responses = "\n\n".join(f"### {l}\n{t}" for l, t in state["responses"].items())
    reviews = "\n".join(
        f"- {r['label']}: accuracy {r['accuracy']}/5, completeness {r['completeness']}/5, "
        f"reasoning {r['reasoning']}/5. Unsupported: {r['unsupported_claims'] or 'none'}. "
        f"Missed: {r['missed'] or 'none'}. Verdict: {r['verdict']}"
        for r in state.get("reviews", [])
    ) or "(no peer reviews available)"
    # out: FinalAnswer = get_model(CHAIRMAN).with_structured_output(FinalAnswer).invoke([
    out: FinalAnswer = structured(CHAIRMAN, FinalAnswer).invoke([
        SystemMessage(CHAIRMAN_SYSTEM),
        HumanMessage(f"Question:\n{state['question']}\n\nPanel responses:\n\n{responses}\n\nPeer reviews:\n{reviews}"),
    ])
    return {"final": out.model_dump()}


def build_graph():
    g = StateGraph(CouncilState)
    g.add_node("draft", draft)
    g.add_node("anonymize", anonymize)
    g.add_node("review", review)
    g.add_node("chairman", chairman)
    g.add_conditional_edges(START, dispatch_drafts, ["draft"])
    g.add_edge("draft", "anonymize")
    g.add_conditional_edges("anonymize", dispatch_reviews, ["review"])
    g.add_edge("review", "chairman")
    g.add_edge("chairman", END)
    return g.compile()


def run_baseline(question: str) -> str:
    """Single strong model, no council. Use it to check whether the council is actually worth its cost."""
    return to_text(get_model(CHAIRMAN).invoke([HumanMessage(question)]))
