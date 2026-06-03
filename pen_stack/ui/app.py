"""PEN-STACK — The Writable Genome | Streamlit atlas browser.

A scientific front-end over the 3M-locus Writable Genome atlas. Two core queries:
  - Forward:  a gene/coordinate -> is it safe + durable to WRITE here?  (decomposed verdict)
  - Inverse:  a disease gene    -> the top-N safest, most durable writable loci within a window.
Plus an atlas genome browser, the blind-validation dashboard, and cross-cell-type comparison.

Run:  streamlit run pen_stack/ui/app.py
Data: set PEN_ATLAS_DIR (default: ./data or Final_Part_v3.0/phase_1/out). Needs atlas_<ct>.parquet,
      gene_coords.parquet, and (optional) validation_report.json.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# ----------------------------------------------------------------------------- config / theme
st.set_page_config(page_title="PEN-STACK · The Writable Genome", page_icon="🧬",
                   layout="wide", initial_sidebar_state="expanded")

CSS = """
<style>
:root { --ink:#05080f; --panel:#0c1322; --line:#1c2840; --cyan:#37e6e0; --green:#3dffa2;
        --amber:#ffc857; --red:#ff5d6c; --txt:#dfe9ff; --mut:#7e8db5; }
.stApp { background: radial-gradient(1200px 700px at 80% -10%, #10203f 0%, var(--ink) 55%); color:var(--txt); }
section[data-testid="stSidebar"] { background:#070c17; border-right:1px solid var(--line); }
h1,h2,h3,h4 { color:var(--txt); font-family:'Segoe UI',system-ui,sans-serif; letter-spacing:.2px; }
.mono { font-family:'JetBrains Mono','Consolas',monospace; }
.hero { font-size:2.5rem; font-weight:800; line-height:1.05;
        background:linear-gradient(90deg,var(--cyan),var(--green)); -webkit-background-clip:text;
        -webkit-text-fill-color:transparent; }
.sub { color:var(--mut); font-size:1.02rem; }
.card { background:linear-gradient(180deg,var(--panel),#0a1020); border:1px solid var(--line);
        border-radius:16px; padding:18px 20px; box-shadow:0 0 0 1px rgba(55,230,224,.04), 0 18px 40px -28px #000; }
.kpi { font-size:2.1rem; font-weight:800; }
.kpi-l { color:var(--mut); font-size:.78rem; text-transform:uppercase; letter-spacing:.16em; }
.verdict { border-radius:16px; padding:18px 24px; font-weight:800; font-size:1.5rem; border:1px solid; }
.v-go  { background:rgba(61,255,162,.08); border-color:var(--green); color:var(--green); }
.v-cau { background:rgba(255,200,87,.08); border-color:var(--amber); color:var(--amber); }
.v-no  { background:rgba(255,93,108,.08); border-color:var(--red); color:var(--red); }
.badge { display:inline-block; padding:2px 10px; border:1px solid var(--line); border-radius:999px;
         color:var(--cyan); font-size:.72rem; margin-right:6px; }
.stDataFrame { border:1px solid var(--line); border-radius:12px; }
hr { border-color:var(--line); }
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)
PLOTLY = dict(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
              font=dict(color="#dfe9ff"), margin=dict(l=10, r=10, t=30, b=10))
CT_LABEL = {"k562": "K562 (erythroleukemia)", "hepg2": "HepG2 (hepatocellular)",
            "hspc": "HSPC (CD34+ progenitor)"}


# ----------------------------------------------------------------------------- data loading
def _data_dir() -> Path:
    for c in [os.environ.get("PEN_ATLAS_DIR"), "data", "Final_Part_v3.0/phase_1/out",
              str(Path(__file__).resolve().parents[2] / ".." / "phase_1" / "out")]:
        if c and (Path(c) / "atlas_k562.parquet").exists():
            return Path(c)
    return Path(os.environ.get("PEN_ATLAS_DIR", "data"))


DATA = _data_dir()
BIN_BP = 1000


@st.cache_data(show_spinner=False)
def load_atlas(ct: str) -> pd.DataFrame:
    df = pd.read_parquet(DATA / f"atlas_{ct}.parquet")
    for col in ("writability", "safety", "p_durable"):
        df[f"{col}_pct"] = df[col].rank(pct=True)
    return df


@st.cache_data(show_spinner=False)
def load_genes() -> pd.DataFrame:
    for p in [DATA / "gene_coords.parquet", DATA.parent / "app_data" / "gene_coords.parquet"]:
        if p.exists():
            return pd.read_parquet(p)
    return pd.DataFrame(columns=["chrom", "start", "end", "strand", "gene"])


@st.cache_data(show_spinner=False)
def load_validation() -> dict | None:
    p = DATA / "validation_report.json"
    return json.loads(p.read_text()) if p.exists() else None


@st.cache_data(show_spinner=False)
def load_writer_atlas() -> pd.DataFrame:
    """Phase-2 Writer Atlas (33k systems x measured axes). Ships inside the package."""
    p = Path(__file__).resolve().parents[1] / "atlas" / "atlas.parquet"
    return pd.read_parquet(p) if p.exists() else pd.DataFrame()


def region_bins(df, chrom, start, end):
    return df[(df.chrom == chrom) & (df.bin * BIN_BP >= start) & (df.bin * BIN_BP <= end)]


def verdict(writ_pct, safety_pct):
    if safety_pct < 0.15 or writ_pct < 0.20:
        return "AVOID — high genotoxic risk / poor durability", "v-no"
    if writ_pct < 0.55:
        return "CAUTION — sub-optimal; consider nearby alternatives", "v-cau"
    return "WRITABLE — safe & durable insertion locus", "v-go"


# ----------------------------------------------------------------------------- viz helpers
def gauge(value, title, color):
    fig = go.Figure(go.Indicator(
        mode="gauge+number", value=value * 100, number={"suffix": "%", "font": {"size": 34}},
        title={"text": title, "font": {"size": 14}},
        gauge={"axis": {"range": [0, 100], "tickcolor": "#7e8db5"},
               "bar": {"color": color}, "bgcolor": "rgba(0,0,0,0)",
               "borderwidth": 1, "bordercolor": "#1c2840",
               "steps": [{"range": [0, 20], "color": "rgba(255,93,108,.18)"},
                         {"range": [20, 55], "color": "rgba(255,200,87,.14)"},
                         {"range": [55, 100], "color": "rgba(61,255,162,.14)"}]}))
    fig.update_layout(height=230, **PLOTLY)
    return fig


def track_fig(sub, center=None):
    fig = go.Figure()
    x = sub.bin * BIN_BP / 1e6
    fig.add_trace(go.Scatter(x=x, y=sub.writability, name="writability", mode="lines",
                             line=dict(color="#3dffa2", width=1.5), fill="tozeroy",
                             fillcolor="rgba(61,255,162,.12)"))
    fig.add_trace(go.Scatter(x=x, y=sub.safety, name="safety", mode="lines",
                             line=dict(color="#37e6e0", width=1)))
    fig.add_trace(go.Scatter(x=x, y=sub.p_durable, name="durability", mode="lines",
                             line=dict(color="#ffc857", width=1)))
    if center is not None:
        fig.add_vline(x=center / 1e6, line_color="#ff5d6c", line_dash="dot")
    fig.update_layout(height=300, xaxis_title="position (Mb)", yaxis_title="score",
                      legend=dict(orientation="h", y=1.15), **PLOTLY)
    return fig


# ----------------------------------------------------------------------------- sidebar
st.sidebar.markdown("## 🧬 PEN-STACK")
st.sidebar.caption("The Writable Genome · v3.0")
page = st.sidebar.radio("Navigate", ["Overview", "Forward query", "Site finder (inverse)",
                                     "Atlas browser", "Validation", "Cross-cell-type",
                                     "Writer Atlas", "Bridge design", "Write Planner", "Ask (RAG)",
                                     "Agent"])
_available_cts = sorted(p.stem.replace("atlas_", "") for p in DATA.glob("atlas_*.parquet")
                        if p.stem.replace("atlas_", "") in CT_LABEL) or ["k562"]
ct = st.sidebar.selectbox("Cell type", _available_cts, format_func=lambda c: CT_LABEL.get(c, c.upper()))
st.sidebar.markdown("---")
st.sidebar.caption("Writability = **safety × durability × reachability**, learned blind on public data.")
if not (DATA / "atlas_k562.parquet").exists():
    st.sidebar.error(f"Atlas not found in {DATA}. Set PEN_ATLAS_DIR.")
    st.stop()

genes = load_genes()


def gene_row(name):
    r = genes[genes.gene.str.upper() == name.strip().upper()]
    return None if r.empty else r.iloc[0]


# ----------------------------------------------------------------------------- pages
if page == "Overview":
    st.markdown('<div class="hero">The Writable Genome</div>', unsafe_allow_html=True)
    st.markdown('<p class="sub">A predictive, writer-aware atlas of <b>where in the genome you can '
                'safely and durably write new DNA</b> — and which enzyme can write it there.</p>',
                unsafe_allow_html=True)
    df = load_atlas(ct)
    c = st.columns(4)
    kpis = [("loci scored", f"{len(df):,}"), ("cell type", ct.upper()),
            ("mean writability", f"{df.writability.mean():.2f}"),
            ("median safety", f"{df.safety.median():.2f}")]
    for col, (lab, val) in zip(c, kpis):
        col.markdown(f'<div class="card"><div class="kpi-l">{lab}</div>'
                     f'<div class="kpi mono">{val}</div></div>', unsafe_allow_html=True)
    st.markdown("####")
    left, right = st.columns([2, 1])
    with left:
        st.markdown("##### Genome-wide writability distribution")
        h = go.Figure(go.Histogram(x=df.writability, nbinsx=60, marker_color="#37e6e0"))
        h.update_layout(height=320, xaxis_title="writability score", yaxis_title="loci", **PLOTLY)
        st.plotly_chart(h, use_container_width=True)
    with right:
        st.markdown("##### Three learned layers")
        st.markdown('<div class="card mono">'
                    '<span class="badge">SAFETY</span> genotoxicity risk<br>'
                    '<span style="color:#7e8db5">COSMIC · DepMap · 3.7M MLV sites</span><br><br>'
                    '<span class="badge">DURABILITY</span> will it stay expressed<br>'
                    '<span style="color:#7e8db5">TRIP position-effect model</span><br><br>'
                    '<span class="badge">REACHABILITY</span> which writer reaches it<br>'
                    '<span style="color:#7e8db5">Writer-Targeting KB (8 families)</span></div>',
                    unsafe_allow_html=True)
    v = load_validation()
    if v:
        st.markdown("##### Blind validation — all pre-registered checks")
        cols = st.columns(len(v.get("prereg_checks", {})) or 1)
        for col, (k, ok) in zip(cols, v.get("prereg_checks", {}).items()):
            col.markdown(f'<div class="card"><div class="kpi-l">{k}</div>'
                         f'<div class="kpi" style="color:{"#3dffa2" if ok else "#ff5d6c"}">'
                         f'{"PASS" if ok else "FAIL"}</div></div>', unsafe_allow_html=True)

elif page == "Forward query":
    st.markdown("### Forward query — *is it safe to write here?*")
    df = load_atlas(ct)
    c1, c2, c3 = st.columns([2, 1, 1])
    q = c1.text_input("Gene symbol or coordinate (chr:pos)", "AAVS1")
    win = c2.number_input("window (kb)", 1, 200, 20)
    go_btn = c3.button("Evaluate", type="primary", use_container_width=True)
    alias = {"AAVS1": "PPP1R12C"}
    if go_btn or q:
        chrom = start = end = None
        if ":" in q:
            chrom, pos = q.split(":")[0], int(q.split(":")[1].replace(",", ""))
            start, end = pos - win * 1000, pos + win * 1000
        else:
            gr = gene_row(alias.get(q.strip().upper(), q))
            if gr is not None:
                chrom, start, end = gr.chrom, gr.start - win * 1000, gr.end + win * 1000
        if chrom is None:
            st.warning("Gene/coordinate not found.")
        else:
            sub = region_bins(df, chrom, max(0, start), end)
            if sub.empty:
                st.warning("No atlas bins in that region.")
            else:
                wr, sf, du = sub.writability.mean(), sub.safety.mean(), sub.p_durable.mean()
                wrp = float((df.writability < wr).mean())
                sfp = float((df.safety < sf).mean())
                msg, cls = verdict(wrp, sfp)
                st.markdown(f'<div class="verdict {cls}">{msg}</div>', unsafe_allow_html=True)
                st.caption(f"{chrom}:{max(0,start):,}-{end:,}  ·  {CT_LABEL[ct]}  ·  {len(sub)} loci")
                g = st.columns(3)
                g[0].plotly_chart(gauge(wr, "Writability", "#3dffa2"), use_container_width=True)
                g[1].plotly_chart(gauge(sf, "Safety", "#37e6e0"), use_container_width=True)
                g[2].plotly_chart(gauge(du, "Durability", "#ffc857"), use_container_width=True)
                st.markdown("##### Local writability landscape")
                st.plotly_chart(track_fig(sub, center=(start + end) // 2), use_container_width=True)
                st.markdown('<span class="badge">reachable writers</span> '
                            f'<span class="mono">{sub.reachable_tier1.iloc[0]}</span> '
                            '<span style="color:#7e8db5">(Tier-1, locus-level)</span>',
                            unsafe_allow_html=True)

elif page == "Site finder (inverse)":
    st.markdown("### Site finder — *the safest writable loci near a target*")
    df = load_atlas(ct)
    c1, c2, c3, c4 = st.columns([2, 1, 1, 1])
    gname = c1.text_input("Disease / target gene", "HBB")
    span = c2.number_input("search ±(Mb)", 0.1, 5.0, 1.0)
    topn = c3.number_input("top N", 5, 200, 50)
    find = c4.button("Find sites", type="primary", use_container_width=True)
    if find or gname:
        gr = gene_row(gname)
        if gr is None:
            st.warning("Gene not found.")
        else:
            lo, hi = gr.start - int(span * 1e6), gr.end + int(span * 1e6)
            sub = region_bins(df, gr.chrom, max(0, lo), hi).copy()
            top = sub.nlargest(int(topn), "writability")
            st.caption(f"{gname} ({gr.chrom}:{gr.start:,}) · searching ±{span} Mb · {len(sub)} loci scanned")
            k = st.columns(3)
            k[0].markdown(f'<div class="card"><div class="kpi-l">candidate loci</div>'
                          f'<div class="kpi mono">{len(sub):,}</div></div>', unsafe_allow_html=True)
            k[1].markdown(f'<div class="card"><div class="kpi-l">best writability</div>'
                          f'<div class="kpi mono" style="color:#3dffa2">{top.writability.max():.2f}</div></div>',
                          unsafe_allow_html=True)
            k[2].markdown(f'<div class="card"><div class="kpi-l">target locus writability</div>'
                          f'<div class="kpi mono">{sub[(sub.bin*BIN_BP>=gr.start)&(sub.bin*BIN_BP<=gr.end)].writability.mean():.2f}'
                          '</div></div>', unsafe_allow_html=True)
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=sub.bin * BIN_BP / 1e6, y=sub.writability, mode="markers",
                                     marker=dict(size=4, color=sub.writability, colorscale="Tealgrn",
                                                 showscale=False), name="loci"))
            fig.add_trace(go.Scatter(x=top.bin * BIN_BP / 1e6, y=top.writability, mode="markers",
                                     marker=dict(size=9, color="#3dffa2", line=dict(color="#fff", width=.5)),
                                     name=f"top {topn}"))
            fig.add_vrect(x0=gr.start / 1e6, x1=gr.end / 1e6, fillcolor="rgba(255,93,108,.25)",
                          line_width=0, annotation_text=gname)
            fig.update_layout(height=320, xaxis_title="position (Mb)", yaxis_title="writability",
                              legend=dict(orientation="h", y=1.15), **PLOTLY)
            st.plotly_chart(fig, use_container_width=True)
            out = top[["chrom", "bin", "writability", "safety", "p_durable", "reachable_tier1"]].copy()
            out["position"] = out.bin * BIN_BP
            out = out[["chrom", "position", "writability", "safety", "p_durable", "reachable_tier1"]]
            st.markdown(f"##### Top {topn} writable loci")
            st.dataframe(out.round(3), use_container_width=True, height=360)
            st.download_button("⬇ Download ranked loci (CSV)", out.to_csv(index=False),
                               f"writable_loci_{gname}_{ct}.csv", "text/csv")

elif page == "Atlas browser":
    st.markdown("### Atlas browser — *genome-wide tracks*")
    df = load_atlas(ct)
    c1, c2, c3 = st.columns([1, 2, 2])
    chrom = c1.selectbox("chromosome", sorted(df.chrom.unique(), key=lambda x: (len(x), x)))
    cmax = int(df[df.chrom == chrom].bin.max() * BIN_BP)
    rng = c2.slider("region (Mb)", 0.0, cmax / 1e6, (0.0, min(5.0, cmax / 1e6)), step=0.5)
    c3.markdown("####")
    sub = region_bins(df, chrom, int(rng[0] * 1e6), int(rng[1] * 1e6))
    if len(sub) > 8000:
        sub = sub.iloc[:: len(sub) // 8000]
    st.plotly_chart(track_fig(sub), use_container_width=True)
    st.caption(f"{chrom}:{int(rng[0]*1e6):,}-{int(rng[1]*1e6):,} · {len(sub):,} bins shown · {CT_LABEL[ct]}")

elif page == "Validation":
    st.markdown("### Blind validation — *recovering known truth*")
    v = load_validation()
    if not v:
        st.info("validation_report.json not found in the data directory.")
    else:
        d = v.get("durability") or {}
        a = v.get("atlas", {})
        c = st.columns(3)
        c[0].markdown(f'<div class="card"><div class="kpi-l">durability Spearman ρ</div>'
                      f'<div class="kpi mono" style="color:#3dffa2">{d.get("expr_spearman",0):.2f}</div></div>',
                      unsafe_allow_html=True)
        c[1].markdown(f'<div class="card"><div class="kpi-l">silenced/stable AUROC</div>'
                      f'<div class="kpi mono">{d.get("silenced_auroc",0):.2f}</div>'
                      f'<div class="kpi-l">baseline {d.get("silenced_baseline_h3k9me3_auroc",0):.2f}</div></div>',
                      unsafe_allow_html=True)
        allok = v.get("all_prereg_checks_pass")
        c[2].markdown(f'<div class="card"><div class="kpi-l">pre-registered checks</div>'
                      f'<div class="kpi" style="color:{"#3dffa2" if allok else "#ff5d6c"}">'
                      f'{"ALL PASS" if allok else "REVIEW"}</div></div>', unsafe_allow_html=True)
        st.markdown("##### Safe harbours vs genotoxic CIS — writability percentile")
        rows = []
        for cell, av in a.items():
            for name, (cls, pct) in av.get("loci", {}).items():
                rows.append({"cell": cell.upper(), "locus": name, "class": cls, "pct": pct})
        if rows:
            rdf = pd.DataFrame(rows)
            fig = go.Figure()
            for cls, color in [("SAFE", "#3dffa2"), ("GTOX", "#ff5d6c")]:
                s = rdf[rdf["class"] == cls]
                fig.add_trace(go.Bar(x=s.locus + " · " + s.cell, y=s.pct, name=cls, marker_color=color))
            fig.update_layout(height=360, yaxis_title="writability percentile",
                              barmode="group", **PLOTLY)
            st.plotly_chart(fig, use_container_width=True)
            st.caption("Validated safe harbours (green) score high; clinical genotoxic loci (red) score "
                       "near zero — recovered blind, never trained on these labels.")

elif page == "Cross-cell-type":
    st.markdown("### Cross-cell-type — *function transfer, reported honestly*")
    a = load_atlas("k562")[["chrom", "bin", "writability"]].rename(columns={"writability": "k562"})
    b = load_atlas("hepg2")[["chrom", "bin", "writability"]].rename(columns={"writability": "hepg2"})
    m = a.merge(b, on=["chrom", "bin"]).sample(min(40000, len(a)), random_state=0)
    rho = float(pd.Series(m.k562).corr(pd.Series(m.hepg2), method="spearman"))
    st.markdown(f'<div class="card"><div class="kpi-l">K562 ↔ HepG2 writability Spearman</div>'
                f'<div class="kpi mono" style="color:#37e6e0">{rho:.2f}</div></div>', unsafe_allow_html=True)
    fig = go.Figure(go.Histogram2d(x=m.k562, y=m.hepg2, colorscale="Tealgrn", nbinsx=50, nbinsy=50))
    fig.update_layout(height=420, xaxis_title="K562 writability", yaxis_title="HepG2 writability", **PLOTLY)
    st.plotly_chart(fig, use_container_width=True)
    st.caption("The model is cell-type-specific in inputs, agnostic in function: writability correlates "
               "across cell types yet differs locus-by-locus — the quantified transfer, not a footnote.")

elif page == "Writer Atlas":
    st.markdown("### Writer Atlas — *every genome-writing family on common, measured axes*")
    wa = load_writer_atlas()
    if wa.empty:
        st.info("atlas.parquet not found — run `python scripts/p2_build_atlas.py`.")
    else:
        cov = (wa.groupby("family")
                 .agg(systems=("representative_system", "size"),
                      measured=("confidence", lambda s: int((s == "measured").sum())),
                      tier=("reachability_tier", "first"),
                      mechanism=("mechanism_bucket", "first"),
                      deliv=("deliv_class", "first"),
                      cargo_bp=("cargo_capacity_bp", "max"))
                 .reset_index().sort_values("systems", ascending=False))
        k = st.columns(3)
        k[0].markdown(f'<div class="card"><div class="kpi-l">writer families</div>'
                      f'<div class="kpi mono">{wa.family.nunique()}</div></div>', unsafe_allow_html=True)
        k[1].markdown(f'<div class="card"><div class="kpi-l">catalogued systems</div>'
                      f'<div class="kpi mono">{len(wa):,}</div></div>', unsafe_allow_html=True)
        k[2].markdown(f'<div class="card"><div class="kpi-l">IS110 orthologs</div>'
                      f'<div class="kpi mono" style="color:#3dffa2">{int((wa.family=="bridge_IS110").sum()):,}</div></div>',
                      unsafe_allow_html=True)
        st.markdown("##### Family coverage (measured axes + reachability tier)")
        st.dataframe(cov, use_container_width=True, height=320)
        fams = st.multiselect("Compare families", sorted(wa.family.unique()),
                              default=["bridge_IS110", "CAST_VK", "serine_integrase", "PE_integrase"])
        comp = wa[wa.family.isin(fams) & wa.entry_kind.eq("curated_core")] if "entry_kind" in wa else wa[wa.family.isin(fams)]
        if not comp.empty and "readiness" in comp:
            fig = go.Figure(go.Bar(x=comp.representative_system, y=comp.readiness,
                                   marker_color="#37e6e0", text=comp.deliv_class))
            fig.update_layout(height=320, yaxis_title="therapeutic readiness",
                              xaxis_title="representative system", **PLOTLY)
            st.plotly_chart(fig, use_container_width=True)
        st.caption("Reachability tiers: Tier-1 directly scannable · Tier-2 candidate (requires validation) "
                   "· Tier-3 not yet predictable. Every system carries a confidence tag + source DOI.")

elif page == "Bridge design":
    st.markdown("### Bridge design + off-target — *the first instrument of PEN-STACK*")
    st.caption("Design a bridge RNA (wraps the Arc BridgeRNADesigner) and assess fold + cross-loop QC and "
               "genome-wide off-target risk (position-weight model; measured profile from Perry 2025).")
    c1, c2 = st.columns(2)
    target = c1.text_input("Target core (14 nt)", "ACGTGTCTACGTGA")
    donor = c2.text_input("Donor core (14 nt)", "TTGCATCTAGGCAC")
    scaffold = st.selectbox("Scaffold", ["ISCro4_enhanced", "ISCro4_WT", "IS621"])
    scan_chrom = st.selectbox("Off-target scan", ["none (QC only)", "chr22", "chr21", "chrX"])
    if st.button("Design + assess", type="primary"):
        from pen_stack.bridge.fold_qc import qc_verdict
        from pen_stack.bridge.ingest import derive_measured_profile
        from pen_stack.bridge.pipeline import design_brna
        brna = design_brna(target, donor, scaffold)
        st.markdown(f'<div class="card"><b>Bridge RNA</b> ({scaffold}) — target {brna["target"]} · '
                    f'donor {brna["donor"]}' +
                    (f' · scaffold {len(brna["bridge_sequence"])} nt' if brna.get("available")
                     else f' · <i>{brna["note"]}</i>') + '</div>', unsafe_allow_html=True)
        qc = qc_verdict(brna["target"], brna["donor"], brna.get("bridge_sequence"))
        vclass = "v-yes" if qc["pass"] else "v-cau"
        st.markdown(f'<div class="verdict {vclass}">QC {"PASS" if qc["pass"] else "REVIEW"} — '
                    f'cross-loop {qc["cross_loop"]}' +
                    (f' · fold MFE {qc["fold"]["mfe"]}' if qc.get("fold", {}).get("available") else "") +
                    '</div>', unsafe_allow_html=True)
        mp = derive_measured_profile()
        if not mp.empty:
            st.caption("Measured off-target position profile (Perry 2025, 6,856 real off-targets) — "
                       "central core (7–9) is the specificity determinant:")
            st.bar_chart(mp.set_index("position")["protective_weight"])
        if scan_chrom != "none (QC only)":
            from pen_stack.bridge.pipeline import _hg38
            fa = _hg38()
            if fa is None:
                st.warning("hg38 fasta not found on this host (set PEN_HG38); QC shown above.")
            else:
                from pen_stack.bridge.offtarget import scan_offtargets
                with st.spinner(f"scanning {scan_chrom} for off-target pseudosites…"):
                    df = scan_offtargets(fa, brna["target"], [scan_chrom])
                st.caption(f"{len(df)} off-target pseudosites on {scan_chrom} "
                           f"({int((df.risk>0.5).sum()) if len(df) else 0} high-risk):")
                if len(df):
                    st.dataframe(df.head(15)[["chrom", "pos", "site", "n_mm", "risk"]].round(3),
                                 use_container_width=True)
        st.caption("Decision-support only; predicted off-targets require experimental validation.")

elif page == "Write Planner":
    st.markdown("### Write Planner — *inverse design (Phase 3 capstone)*")
    st.caption("goal + edit_intent → ranked, traceable site × writer × cargo × delivery plans. "
               "edit_intent is load-bearing (an in-gene site ranks high for knock-in, low for safe-harbour).")
    gene = st.text_input("Target gene", "TRAC")
    intent = st.selectbox("Edit intent", ["knock_in_with_disruption", "safe_harbour_insertion",
                                          "high_durability_insertion", "regulatory_excision", "repeat_excision"])
    cargo_bp = int(st.number_input("Cargo size (bp)", 100, 40000, 2000))
    if st.button("Plan", type="primary"):
        from pen_stack.planner.optimize import EditIntent
        from pen_stack.planner.pipeline import plan_write
        try:
            with st.spinner("optimising destination × writer × cargo × delivery…"):
                plans = plan_write(gene, EditIntent(intent), cargo_bp, ct, k=5)
        except FileNotFoundError as e:
            st.error(str(e))
            plans = []
        if not plans:
            st.warning("No plan found (gene not in the atlas, or no reachable site).")
        for i, p in enumerate(plans, 1):
            s = p["site"]
            st.markdown(f'<div class="card"><b>Plan {i}</b> — {s["chrom"]}:{s["pos"]:,} '
                        f'(on_target={p["on_target"]}) · writer <b>{p["writer"]}</b> '
                        f'[{p["reachability_tier"]}]<br>safety {p["safety"]} · durability {p["durability"]} '
                        f'· writer-activity {p["writer_activity"]} · score {p["score"]}<br>'
                        f'cargo {p["cargo"]["payload_bp"]}bp→{p["cargo"]["assembled_bp"]}bp '
                        f'(size_ok={p["cargo"]["size_ok"]}) · delivery <b>{p["delivery"]["delivery"]}</b> · '
                        f'off-target {p["cargo"].get("offtargets",{}).get("status","n/a")}</div>',
                        unsafe_allow_html=True)
        if plans:
            st.caption(plans[0]["disclaimer"])

elif page == "Ask (RAG)":
    st.markdown("### Ask — *grounded, cited Q&A over the platform*")
    st.caption("Numbers come from validated tool calls (never guessed); clinical-directive questions are refused.")
    q = st.text_input("Ask a question",
                      "Which bridge recombinase works in human cells, and where can I write into CCR5?")
    if st.button("Ask", type="primary") or q:
        from pen_stack.rag.qa import answer as rag_answer
        a = rag_answer(q, ct=ct)
        if a.get("refused"):
            st.markdown(f'<div class="verdict v-no">{a["answer"]}</div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="card">{a["answer"]}</div>', unsafe_allow_html=True)
            if a.get("provenance"):
                st.markdown("##### Tool provenance (every number traces here)")
                st.json(a["provenance"])
            if a.get("citations"):
                st.markdown("##### Citations")
                st.write(", ".join(a["citations"]))
        st.caption(a.get("disclaimer", ""))

elif page == "Agent":
    st.markdown("### Agent — *natural-language goal → cited, auditable write plan*")
    st.caption("The PEN-STACK agent orchestrates every validated tool. It obtains numbers ONLY from tool "
               "calls (no fabrication), refuses clinical directives, and logs an auditable trace.")
    goal = st.text_input("Goal", "Knock a CAR into TRAC, disrupting the TCR for allogeneic CAR-T.")
    if st.button("Plan with agent", type="primary"):
        from pen_stack.agent.orchestrator import run_agent
        with st.spinner("Agent calling validated tools…"):
            res = run_agent(goal)
        if res.get("refused"):
            st.markdown(f'<div class="verdict v-no">{res["plan"]}</div>', unsafe_allow_html=True)
        else:
            mode = "LLM tool-calling" if res.get("llm") else "deterministic fallback (no LLM reachable)"
            st.caption(f"mode: {mode}")
            st.markdown(f'<div class="card">{res["plan"]}</div>', unsafe_allow_html=True)
            if res.get("trace"):
                st.markdown("##### Auditable trace (every number traces to a tool call)")
                for i, step in enumerate(res["trace"], 1):
                    with st.expander(f"step {i}: {step['tool']}({step['args']})"):
                        st.json(step["result"])
        st.caption(res.get("disclaimer", ""))

st.markdown("---")
st.caption("PEN-STACK v3.0 · The Writable Genome + Writer Atlas + Write Planner + agent · decision-support, "
           "not a clinical directive · every score traceable to public data + a pre-registered model.")
