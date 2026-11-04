import pandas as pd
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

from council.config import CHAIRMAN, PANEL  # noqa: E402
from council.graph import build_graph, run_baseline  # noqa: E402

st.set_page_config(page_title="Model Council", page_icon="🏛️", layout="wide")


@st.cache_resource
def get_graph():
    return build_graph()


def run_council(question: str) -> dict:
    result = {"drafts": [], "reviews": [], "errors": []}
    with st.status("Convening the council…", expanded=True) as status:
        try:
            for chunk in get_graph().stream({"question": question}, stream_mode="updates"):
                for node, update in chunk.items():
                    update = update or {}
                    for key, val in update.items():
                        if key in ("drafts", "reviews", "errors"):
                            result[key].extend(val)
                        else:
                            result[key] = val
                    if node == "draft":
                        for d in update.get("drafts", []):
                            st.write(f"✍️ **{d['model']}** drafted independently ({d['seconds']}s)")
                    elif node == "anonymize":
                        st.write("🎭 Responses anonymized and shuffled")
                    elif node == "review":
                        for r in {r["reviewer"] for r in update.get("reviews", [])}:
                            st.write(f"🔍 **{r}** finished blind peer review")
                    elif node == "chairman":
                        st.write("⚖️ Chairman synthesized the final answer")
                    for err in update.get("errors", []):
                        st.write(f"⚠️ {err}")
            status.update(label="Council complete", state="complete", expanded=False)
        except Exception as e:
            status.update(label="Council failed", state="error")
            result["fatal"] = str(e)
    return result


def render(result: dict):
    if result.get("fatal"):
        st.error(result["fatal"])
        return
    final = result.get("final")
    if not final:
        st.warning("No final answer was produced.")
        return
    l2m = result.get("label_to_model", {})
    tab_final, tab_drafts, tab_reviews, tab_base = st.tabs(
        ["Final answer", "Independent drafts", "Peer review", "Single-model baseline"]
    )

    with tab_final:
        icon = {"low": "🔴", "medium": "🟡", "high": "🟢"}[final["confidence"]]
        c1, c2 = st.columns([3, 1])
        c1.markdown(final["answer"])
        c2.metric("Confidence", f"{icon} {final['confidence'].title()}")
        c2.caption(final["confidence_rationale"])
        if final["needs_human_review"]:
            c2.warning("Human review recommended")
        a, d = st.columns(2)
        with a:
            st.subheader("Agreement")
            for x in final["agreements"] or ["—"]:
                st.markdown(f"- {x}")
        with d:
            st.subheader("Disagreement")
            for x in final["disagreements"] or ["—"]:
                st.markdown(f"- {x}")

    with tab_drafts:
        st.caption("Labels were blind during review; the author is revealed here.")
        for label, text in result.get("responses", {}).items():
            with st.expander(f"{label} — written by {l2m.get(label, '?')}"):
                st.markdown(text)

    with tab_reviews:
        if not result["reviews"]:
            st.info("No peer reviews were produced.")
        else:
            df = pd.DataFrame(result["reviews"])
            df["overall"] = df[["accuracy", "completeness", "reasoning"]].mean(axis=1)
            scores = df.groupby("label")[["accuracy", "completeness", "reasoning", "overall"]].mean().round(2)
            scores.insert(0, "author", scores.index.map(l2m))
            st.dataframe(scores, width="stretch")
            st.bar_chart(scores.set_index("author")["overall"])
            for r in result["reviews"]:
                with st.expander(f"{r['reviewer']} on {r['label']} ({l2m.get(r['label'], '?')}) — {r['verdict']}"):
                    st.markdown("**Unsupported claims**")
                    for x in r["unsupported_claims"] or ["none"]:
                        st.markdown(f"- {x}")
                    st.markdown("**Missed**")
                    for x in r["missed"] or ["none"]:
                        st.markdown(f"- {x}")

    with tab_base:
        if "baseline" in result:
            st.markdown(result["baseline"])
        else:
            st.info("Enable 'Also run single-model baseline' in the sidebar.")


with st.sidebar:
    st.header("Panel")
    for p in PANEL:
        st.markdown(f"**{p.name}** · `{p.provider}:{p.model}`")
    st.markdown(f"**Chairman** · `{CHAIRMAN.provider}:{CHAIRMAN.model}`")
    run_base = st.checkbox("Also run single-model baseline", help="Answers with the chairman model alone, for comparison.")
    st.caption("A full run makes ~7 LLM calls. Best for ambiguous, multi-step or high-stakes questions.")

st.title("🏛️ Multi-Model Council")
st.caption("Independent drafts → blind peer review → chairman synthesis")

question = st.text_area("Question", height=140, placeholder="Ask something where being wrong would matter…")
if st.button("Convene council", type="primary", disabled=not question.strip()):
    res = run_council(question.strip())
    if run_base and not res.get("fatal"):
        with st.spinner("Running single-model baseline…"):
            try:
                res["baseline"] = run_baseline(question.strip())
            except Exception as e:
                res["baseline"] = f"Baseline failed: {e}"
    st.session_state["result"] = res

if "result" in st.session_state:
    render(st.session_state["result"])
