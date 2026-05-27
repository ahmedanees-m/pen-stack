"""Streamlit webserver for PEN-COMPARE. 5 tabs matching 5 use cases.

Loads parquets when available (Docker), falls back to data/cache/*.json (Streamlit Cloud).
Q&A tab requires Ollama — degrades gracefully when unavailable.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# ── Paths ────────────────────────────────────────────────────────────────────

ROOT = Path(__file__).resolve().parent.parent.parent  # /workspace/pen-compare
CACHE_DIR = ROOT / "data" / "cache"
_SC = ROOT / "results" / "truewriter_scorecard_v3.2.parquet"
_UN = ROOT / "data" / "unified_editor_universe.parquet"
_DI = ROOT / "results" / "triangulation_discrepancies.parquet"

TIER_COLORS = {
    "TRUE_WRITER": "#1f7a1f",
    "PROBABLE_WRITER": "#b38600",
    "EMERGING_WRITER": "#0066cc",
    "NOT_WRITER": "#cc0000",
}
TIER_ORDER = ["TRUE_WRITER", "PROBABLE_WRITER", "EMERGING_WRITER", "NOT_WRITER"]
GATE_COLS = [
    "g1_dsb_passes",
    "g2_prog_passes",
    "g3_cargo_passes",
    "g4_size_passes",
    "g5_evidence_passes",
]
GATE_NAMES = [
    "G1 DSB Avoidance",
    "G2 Programmability",
    "G3 Native Cargo",
    "G4 Deliverability",
    "G5 Evidence",
]
AXIS_KEYS = ["s_dsb", "s_prog", "s_cargo", "penscore"]
AXIS_LABELS = ["S_DSB", "S_Prog", "S_Cargo", "PenScore"]


# ── Data loaders ─────────────────────────────────────────────────────────────


def _load_parquet_or_json(parquet_path: Path, json_name: str) -> pd.DataFrame:
    if parquet_path.exists():
        return pd.read_parquet(parquet_path)
    j = CACHE_DIR / json_name
    if j.exists():
        return pd.read_json(j)
    return pd.DataFrame()


@st.cache_data(show_spinner=False)
def load_scorecard() -> pd.DataFrame:
    return _load_parquet_or_json(_SC, "scorecard.json")


@st.cache_data(show_spinner=False)
def load_universe() -> pd.DataFrame:
    # Full universe from parquet; natural-only JSON fallback for Cloud
    if _UN.exists():
        return pd.read_parquet(_UN)
    j = CACHE_DIR / "universe_natural.json"
    if j.exists():
        return pd.read_json(j)
    return pd.DataFrame()


@st.cache_data(show_spinner=False)
def load_discrepancies() -> pd.DataFrame:
    return _load_parquet_or_json(_DI, "triangulation_discrepancies.json")


@st.cache_resource(show_spinner=False)
def get_qa():
    """Return PenStackQA instance or None if Ollama/ChromaDB unavailable."""
    try:
        from pen_stack.compare.rag.qa import PenStackQA  # type: ignore[import]

        db = ROOT / "data" / "rag_db"
        if not db.exists():
            return None
        qa = PenStackQA(db_path=db)
        return qa if qa.collection_count() > 0 else None
    except Exception:
        return None


# ── App setup ────────────────────────────────────────────────────────────────

st.set_page_config(page_title="PEN-COMPARE", layout="wide", page_icon="🧬")

scorecard = load_scorecard()
universe = load_universe()
disc = load_discrepancies()

# Merge universe + tier for display
_sc_cols = ["entity_id", "tier", "qualifying_passed", "has_cell_based"] + GATE_COLS
_sc_cols_present = [c for c in _sc_cols if c in scorecard.columns]
if not scorecard.empty and not universe.empty:
    merged = universe.merge(scorecard[_sc_cols_present], on="entity_id", how="left")
else:
    merged = universe.copy()

# Metadata banner
n_entities = len(scorecard) if not scorecard.empty else "?"
st.title("PEN-COMPARE")
st.caption(
    f"Hierarchical Certification Framework for Non-Destructive Genome Editors · "
    f"v0.1.0 · {n_entities:,} entities · "
    f"Pre-registration: [prereg-v3.2](https://osf.io/4kdvy)"
)

tab1, tab2, tab3, tab4, tab5 = st.tabs(
    [
        "🔍 Comparator",
        "🏆 True Writers",
        "🧪 Triangulation",
        "💬 Q&A",
        "🔬 Designer Filter",
    ]
)


# ── Tab 1: Comparator ────────────────────────────────────────────────────────


def _safe_float(val) -> float:
    try:
        f = float(val)
        return 0.0 if f != f else f  # NaN → 0
    except (TypeError, ValueError):
        return 0.0


with tab1:
    st.header("Side-by-side editor comparison")

    if merged.empty:
        st.warning("No entity data available.")
    else:
        all_ids = sorted(merged["entity_id"].unique().tolist())
        default_a = all_ids.index("ISCro4") if "ISCro4" in all_ids else 0
        default_b = all_ids.index("IS621") if "IS621" in all_ids else min(1, len(all_ids) - 1)

        c1, c2 = st.columns(2)
        with c1:
            ea = st.selectbox("Editor A", all_ids, index=default_a, key="cmp_a")
        with c2:
            eb = st.selectbox("Editor B", all_ids, index=default_b, key="cmp_b")

        row_a = merged[merged["entity_id"] == ea]
        row_b = merged[merged["entity_id"] == eb]

        if not row_a.empty and not row_b.empty:
            ra, rb = row_a.iloc[0], row_b.iloc[0]

            # Tier badges
            tc1, tc2 = st.columns(2)
            for col, name, row in [(tc1, ea, ra), (tc2, eb, rb)]:
                tier = str(row.get("tier", "—"))
                color = TIER_COLORS.get(tier, "#888")
                with col:
                    st.markdown(
                        f"**{name}** &nbsp; "
                        f"<span style='background:{color};color:white;padding:3px 10px;"
                        f"border-radius:4px;font-weight:bold'>{tier}</span>",
                        unsafe_allow_html=True,
                    )

            st.markdown("---")

            # Radar chart
            vals_a = [_safe_float(ra.get(k)) for k in AXIS_KEYS] + [
                _safe_float(ra.get(AXIS_KEYS[0]))
            ]
            vals_b = [_safe_float(rb.get(k)) for k in AXIS_KEYS] + [
                _safe_float(rb.get(AXIS_KEYS[0]))
            ]
            theta = AXIS_LABELS + [AXIS_LABELS[0]]

            fig = go.Figure()
            fig.add_trace(
                go.Scatterpolar(
                    r=vals_a,
                    theta=theta,
                    fill="toself",
                    name=ea,
                    line=dict(color="#1f7a1f", width=2),
                )
            )
            fig.add_trace(
                go.Scatterpolar(
                    r=vals_b,
                    theta=theta,
                    fill="toself",
                    name=eb,
                    line=dict(color="#cc7700", width=2),
                    opacity=0.75,
                )
            )
            fig.update_layout(
                polar=dict(radialaxis=dict(visible=True, range=[0, 1], tickfont=dict(size=11))),
                height=380,
                legend=dict(x=0.85, y=1.1),
            )
            st.plotly_chart(fig, use_container_width=True)

            # Gate table
            gate_df = pd.DataFrame(
                {
                    "Gate": GATE_NAMES,
                    ea: ["✅" if ra.get(c) else "❌" for c in GATE_COLS],
                    eb: ["✅" if rb.get(c) else "❌" for c in GATE_COLS],
                }
            )
            st.dataframe(gate_df, hide_index=True, use_container_width=True)

            # Axis score table
            ax_rows = [
                {
                    "Axis": lbl,
                    ea: f"{_safe_float(ra.get(k)):.3f}",
                    eb: f"{_safe_float(rb.get(k)):.3f}",
                }
                for k, lbl in zip(AXIS_KEYS, AXIS_LABELS)
            ]
            st.dataframe(pd.DataFrame(ax_rows), hide_index=True, use_container_width=True)


# ── Tab 2: True Writers ──────────────────────────────────────────────────────

with tab2:
    st.header("TrueWriterScore tier distribution")

    if scorecard.empty:
        st.warning("Scorecard data unavailable.")
    else:
        tier_counts = scorecard["tier"].value_counts()
        tc_df = pd.DataFrame(
            {
                "Tier": TIER_ORDER,
                "Count": [tier_counts.get(t, 0) for t in TIER_ORDER],
            }
        )
        fig2 = go.Figure(
            go.Bar(
                x=tc_df["Tier"],
                y=tc_df["Count"],
                marker_color=[TIER_COLORS[t] for t in TIER_ORDER],
                text=tc_df["Count"],
                textposition="auto",
            )
        )
        fig2.update_layout(height=320, xaxis_title="", yaxis_title="Count", showlegend=False)
        st.plotly_chart(fig2, use_container_width=True)

        col_a, col_b = st.columns(2)
        with col_a:
            st.subheader("TRUE_WRITER editors")
            tw = scorecard[scorecard["tier"] == "TRUE_WRITER"]
            cols_tw = [c for c in ["entity_id", "source", "qualifying_passed"] if c in tw.columns]
            st.dataframe(
                tw[cols_tw].reset_index(drop=True), hide_index=True, use_container_width=True
            )

        with col_b:
            st.subheader("Natural editors — all tiers")
            nat_sc = (
                scorecard[scorecard["source"] == "natural"]
                if "source" in scorecard.columns
                else scorecard
            )
            cols_nat = [
                c
                for c in ["entity_id", "tier", "qualifying_passed", "has_cell_based"]
                if c in nat_sc.columns
            ]
            st.dataframe(
                nat_sc[cols_nat].reset_index(drop=True), hide_index=True, use_container_width=True
            )


# ── Tab 3: Triangulation ─────────────────────────────────────────────────────

with tab3:
    st.header("Cross-pipeline triangulation")

    if disc.empty:
        st.warning("Triangulation data unavailable.")
    else:
        n_disc = len(disc)
        p3_pass = n_disc >= 5
        st.metric(
            "Total discrepancy records",
            n_disc,
            delta="P3 PASS ✅" if p3_pass else "P3 FAIL ❌",
            delta_color="normal" if p3_pass else "inverse",
        )

        col1, col2 = st.columns(2)

        with col1:
            st.subheader("By category")
            cat_df = disc["category"].value_counts().reset_index()
            cat_df.columns = ["Category", "Count"]
            fig3a = go.Figure(
                go.Bar(x=cat_df["Category"], y=cat_df["Count"], marker_color="#0066cc")
            )
            fig3a.update_layout(height=280, xaxis_tickangle=-20)
            st.plotly_chart(fig3a, use_container_width=True)

        with col2:
            st.subheader("By severity")
            sev_df = disc["severity"].value_counts().reset_index()
            sev_df.columns = ["Severity", "Count"]
            sev_colors = {"high": "#cc0000", "medium": "#ff8800", "low": "#ffcc00"}
            fig3b = go.Figure(
                go.Bar(
                    x=sev_df["Severity"],
                    y=sev_df["Count"],
                    marker_color=[sev_colors.get(s, "#888") for s in sev_df["Severity"]],
                )
            )
            fig3b.update_layout(height=280)
            st.plotly_chart(fig3b, use_container_width=True)

        sev_filter = st.selectbox("Filter by severity", ["All", "high", "medium", "low"])
        disp = disc if sev_filter == "All" else disc[disc["severity"] == sev_filter]
        cols_d = [
            c
            for c in ["entity_id", "category", "severity", "sources_involved", "details"]
            if c in disp.columns
        ]
        st.dataframe(disp[cols_d].reset_index(drop=True), hide_index=True, use_container_width=True)


# ── Tab 4: Q&A ───────────────────────────────────────────────────────────────

with tab4:
    st.header("Ask PEN-STACK Q&A")
    st.caption(
        "Powered by Llama 3.1 8B Instruct via Ollama · RAG index: sentence-transformers/all-MiniLM-L6-v2"
    )

    qa = get_qa()

    if qa is None:
        st.info(
            "The Q&A module requires a local Ollama instance and built RAG index. "
            "Available when running the Docker container with GPU and the `pen-compare-ollama` volume mounted. "
            "See `docker/README.md` for local setup instructions."
        )
        st.markdown("**Example questions you could ask:**")
        for ex in [
            "What is the G1 DSB Avoidance gate threshold?",
            "Which editor is the only TRUE_WRITER?",
            "How many discrepancy records were found in triangulation?",
            "What is ISCro4's UniProt accession?",
        ]:
            st.markdown(f"- *{ex}*")
    else:
        question = st.text_input(
            "Your question:",
            placeholder="What is the G1 DSB Avoidance threshold?",
            key="qa_input",
        )
        if question:
            with st.spinner("Retrieving context and generating answer..."):
                try:
                    answer = qa.ask(question)
                    st.success(answer)
                except Exception as exc:
                    st.warning(f"Q&A error: {exc}")


# ── Tab 5: Designer Filter ───────────────────────────────────────────────────

with tab5:
    st.header("Filter editor universe")

    if merged.empty:
        st.warning("No entity data available.")
    else:
        fa, fb, fc = st.columns(3)
        with fa:
            src_filter = st.selectbox("Source", ["All", "natural", "design"])
        with fb:
            tier_filter = st.selectbox(
                "Minimum tier",
                ["Any", "TRUE_WRITER", "PROBABLE_WRITER", "EMERGING_WRITER"],
            )
        with fc:
            min_ps = st.slider("Min PenScore", 0.0, 1.0, 0.0, step=0.05)

        TIER_RANK = {t: i for i, t in enumerate(reversed(TIER_ORDER))}

        filt = merged.copy()
        if src_filter != "All" and "source" in filt.columns:
            filt = filt[filt["source"] == src_filter]
        if tier_filter != "Any" and "tier" in filt.columns:
            min_rank = TIER_RANK.get(tier_filter, 0)
            filt = filt[filt["tier"].map(TIER_RANK).fillna(-1) >= min_rank]
        if min_ps > 0 and "penscore" in filt.columns:
            filt = filt[filt["penscore"].fillna(0) >= min_ps]

        display_cols = [
            c
            for c in ["entity_id", "source", "tier", "s_dsb", "s_prog", "s_cargo", "penscore"]
            if c in filt.columns
        ]
        st.caption(f"{len(filt):,} entities match filters")
        st.dataframe(
            filt[display_cols].reset_index(drop=True), hide_index=True, use_container_width=True
        )
