// Writer Atlas, compare genome writers across families (confidence, mechanism, cargo capacity, reachability tier,
// measured human-cell activity), AND surface the Stage C writer-efficiency work: a request-ranked recommender that
// carries a candidate learned efficiency with a trained conformal interval (C-WS2), the curated measured-efficiency
// dataset + the held-out Writer-Efficiency-Bench result (C-WS1), and the variant-critique recovery (C-WS4). The
// "measured vs candidate" split is explicit everywhere: the KB ranking is the grounded primary, efficiencies are
// candidate advisories (the learned model does not beat the KB baseline on held-out family at this N).
import React, { useEffect, useMemo, useState } from "react";
import ScoreGuide from "../components/ScoreGuide.jsx";
import { api } from "../api.js";
import { Card, Spinner, ErrorNote, Pill, Stat, Field, Select, Button, Badge } from "../components/ui.jsx";
import { titleCase, num } from "../lib/format.js";

const WRITE_TYPES = ["insertion", "knock_in_with_disruption", "landing_pad_insertion", "high_durability_insertion"];

export default function WriterAtlas() {
  const [coverage, setCoverage] = useState(null);
  const [rows, setRows] = useState(null);
  const [total, setTotal] = useState(0);       // total systems matching the current filter (server-reported)
  const [family, setFamily] = useState("");
  const [tableBusy, setTableBusy] = useState(false);
  const [busy, setBusy] = useState(true);
  const [error, setError] = useState(null);

  // Stage C surfaces
  const [eff, setEff] = useState(null);
  const [immune, setImmune] = useState(null); // v7.1.8: the writer's immunogenicity as an antigen (MHC-II + ADA)
  const [rec, setRec] = useState(null);
  const [recForm, setRecForm] = useState({ write_type: "insertion", cargo_bp: 2000, cell_type: "K562" });
  const [recBusy, setRecBusy] = useState(false);

  // C-WS4 variant critique
  const [vInput, setVInput] = useState("Bxb1");
  const [variants, setVariants] = useState(null);
  const [vBusy, setVBusy] = useState(false);

  useEffect(() => {
    (async () => {
      setBusy(true); setError(null);
      try {
        const [cov, atlas] = await Promise.all([api.atlasCoverage(), api.atlas("", 200)]);
        setCoverage(cov); setRows(atlas.rows || []); setTotal(atlas.n || 0);
      } catch (e) { setError(e); } finally { setBusy(false); }
    })();
    api.writerEfficiency().then(setEff).catch(() => {});
    api.writerImmune().then(setImmune).catch(() => {});
    runRecommend(recForm);
    runVariants("Bxb1");
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  async function runRecommend(form) {
    setRecBusy(true);
    try { setRec(await api.recommend({ ...form, top_k: 8 })); } catch { setRec(null); } finally { setRecBusy(false); }
  }

  async function runVariants(name) {
    setVBusy(true);
    try { setVariants(await api.writerVariants((name || "").trim() || undefined)); }
    catch { setVariants(null); } finally { setVBusy(false); }
  }

  // Load a family's systems server-side on demand (the atlas has 33,370 systems, dominated by bridge_IS110 at
  // ~32k, so a single head() sample never spans all 8 families -- the dropdown is driven by the coverage endpoint).
  async function onFamily(f) {
    setFamily(f); setTableBusy(true);
    try { const a = await api.atlas(f || "", f ? 300 : 200); setRows(a.rows || []); setTotal(a.n || 0); }
    catch (e) { setError(e); } finally { setTableBusy(false); }
  }

  // the authoritative family list comes from /atlas/coverage (all 8 families + system counts), NOT the row sample
  const families = useMemo(
    () => [...(coverage?.coverage || [])].sort((a, b) => (b.n || 0) - (a.n || 0)), [coverage]);
  const confColor = { measured: "var(--ok)", inferred: "var(--warn)", candidate: "var(--muted)" };

  const hof = eff?.benchmark?.held_out_family, hol = eff?.benchmark?.held_out_locus;

  if (busy) return <Card><Spinner label="Loading the Writer Atlas…" /></Card>;
  if (error) return <Card title="Writer Atlas"><ErrorNote error={error} /></Card>;

  return (
    <div className="space-y-4">
      <ScoreGuide
        intro="Compare writer families and systems for a target. Every row is either measured or a labelled candidate. The KB ranking is the grounded primary; the learned integration-efficiency is a candidate advisory with an interval, never the authoritative ranking."
        items={[
          { term: "Confidence", scale: "measured / inferred / candidate", meaning: "measured = backed by human-cell activity data; inferred = partial evidence; candidate = a knowledge-base prediction, labelled as a hypothesis." },
          { term: "Reachability tier", scale: "Tier-1 / 2 / 3", meaning: "How confidently the writer can be AIMED at an arbitrary target. Tier-1 (scannable) = a target-programmable writer whose site is found by scanning the genome (Cas9, Cas12a, bridge IS110) — broadly reachable. Tier-2 (context-candidate) = reachable only in a permissive sequence/chromatin context, a candidate needing experimental confirmation. Tier-3 (not-predictable) = no reliable targeting rule yet — exploratory. Higher tier = more reach you can trust." },
          { term: "Cargo capacity", scale: "bp", meaning: "The per-family payload capacity from the curated atlas; pair it with your cargo size to see which families fit." },
          { term: "Predicted efficiency", scale: "% integration + conformal interval", meaning: "A learned predictor (C-WS2) trained ONLY on the curated real dataset, emitted with a trained split-conformal interval. A candidate advisory — and only for families the dataset actually contains (never extrapolated to an unseen family)." },
          { term: "KB readiness", scale: "0–1, the primary rank", meaning: "A transparent score from the curated atlas (DSB-free + measured activity + cargo headroom). This, not the learned efficiency, is the grounded ranking signal." },
          { term: "Variant critique", scale: "fold over WT", meaning: "For a chosen serine integrase, the measured hyperactive mutants ranked by fold-improvement over wild-type (each DOI-backed). A retrospective catalogue recovery — a blind sequence-only predictor is honestly deferred, not faked." },
        ]}
        caveats={[
          "Pre-registered honest result (gate C-G2): the learned predictor beats the KB family-mean baseline on held-out LOCUS (CI excludes 0) but NOT on held-out FAMILY at N=42, so the KB ranking is retained as primary and the efficiency ships as a candidate.",
          "No efficiency is fabricated for a family the curated dataset never saw; those stay KB-only.",
        ]} />

      <Card title="Writer recommender" subtitle="Rank writer families for a write request: KB readiness (grounded primary) plus a candidate learned efficiency with a conformal interval."
            icon="designer">
        <div className="grid gap-3 sm:grid-cols-4">
          <Field label="Write type">
            <Select value={recForm.write_type} onChange={(v) => setRecForm((f) => ({ ...f, write_type: v }))}
                    options={WRITE_TYPES.map((v) => ({ value: v, label: v.replace(/_/g, " ") }))} />
          </Field>
          <Field label="Cargo bp">
            <input className="input" type="number" min={0} max={200000} step={100} value={recForm.cargo_bp}
                   onChange={(e) => { const n = parseInt(e.target.value || "0", 10);
                     setRecForm((f) => ({ ...f, cargo_bp: Number.isNaN(n) ? 0 : Math.min(200000, Math.max(0, n)) })); }} />
          </Field>
          <Field label="Cell type" hint="a feature of the efficiency model (free-form)">
            <input className="input" value={recForm.cell_type}
                   onChange={(e) => setRecForm((f) => ({ ...f, cell_type: e.target.value }))} />
          </Field>
          <div className="flex items-end"><Button onClick={() => runRecommend(recForm)} disabled={recBusy}>Recommend</Button></div>
        </div>
        {recBusy ? <div className="mt-4"><Spinner label="Ranking writers…" /></div> : rec && (
          <div className="mt-4 overflow-x-auto">
            <table className="w-full text-sm">
              <thead><tr className="border-b border-line text-left text-[11px] uppercase tracking-wide text-fg-faint">
                <th className="py-2 pr-3">Family</th><th className="py-2 pr-3">KB readiness</th>
                <th className="py-2 pr-3">Predicted efficiency</th><th className="py-2 pr-3">Cargo fit</th>
                <th className="py-2">Confidence</th></tr></thead>
              <tbody>
                {(rec.recommendations || []).map((r, i) => (
                  <tr key={i} className="border-b border-line/50">
                    <td className="py-2 pr-3 font-medium">{titleCase(r.family)}</td>
                    <td className="py-2 pr-3 tabular-nums text-brand">{num(r.kb_readiness)}</td>
                    <td className="py-2 pr-3 tabular-nums">
                      {r.predicted_efficiency_pct == null
                        ? <span className="text-fg-faint">KB-only (family unseen)</span>
                        : <span><b>{r.predicted_efficiency_pct}%</b>
                            <span className="text-fg-faint"> [{r.efficiency_interval_pct?.[0]}–{r.efficiency_interval_pct?.[1]}]</span>
                            <Badge tone="warn">candidate</Badge></span>}
                    </td>
                    <td className="py-2 pr-3">{r.cargo_fit == null ? "n/a" : r.cargo_fit
                      ? <span className="text-ok">fits</span> : <span className="text-bad">over capacity</span>}</td>
                    <td className="py-2"><Pill color={confColor[r.confidence] || "var(--muted)"}>{r.confidence}</Pill></td>
                  </tr>
                ))}
              </tbody>
            </table>
            <p className="mt-2 text-[11px] text-fg-faint">{rec.note}</p>
          </div>
        )}
      </Card>

      {eff && (
        <Card title="Measured efficiency dataset + held-out validation"
              subtitle="The curated, DOI-backed integration-efficiency dataset (C-WS1) and the Writer-Efficiency-Bench result (C-WS2)." icon="experiments">
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            <Stat label="Measured records" value={eff.dataset_summary?.n_records} />
            <Stat label="Human-cell rows" value={eff.dataset_summary?.n_human} />
            <Stat label="Families" value={Object.keys(eff.dataset_summary?.by_family || {}).length} />
            <Stat label="DOIs" value={eff.dataset_summary?.n_dois} />
          </div>
          {(hof || hol) && (
            <div className="mt-3 grid gap-2 sm:grid-cols-2">
              <div className="rounded-lg border border-line bg-ink-900 p-3 text-xs">
                <div className="font-medium text-fg">Held-out family</div>
                <div className="mt-1 text-fg-dim">MAE {num(hof?.mae_model)} vs baseline {num(hof?.mae_baseline_family_mean)} · Spearman {num(hof?.spearman_model)}</div>
                <div className="mt-1">{hof?.delta?.model_beats_baseline
                  ? <span className="text-ok">beats baseline (CI excludes 0)</span>
                  : <span className="text-warn">does NOT beat baseline — CI [{num(hof?.delta?.ci95?.[0])}, {num(hof?.delta?.ci95?.[1])}] includes 0</span>}</div>
              </div>
              <div className="rounded-lg border border-line bg-ink-900 p-3 text-xs">
                <div className="font-medium text-fg">Held-out locus</div>
                <div className="mt-1 text-fg-dim">MAE {num(hol?.mae_model)} vs baseline {num(hol?.mae_baseline_family_mean)} · Spearman {num(hol?.spearman_model)}</div>
                <div className="mt-1">{hol?.delta?.model_beats_baseline
                  ? <span className="text-ok">beats baseline — CI [{num(hol?.delta?.ci95?.[0])}, {num(hol?.delta?.ci95?.[1])}] excludes 0</span>
                  : <span className="text-warn">does not beat baseline</span>}</div>
              </div>
            </div>
          )}
          {eff.benchmark?.gate_C_G2 && (
            <p className="mt-2 rounded-lg border border-warn/25 bg-warn/5 px-3 py-2 text-[11px] leading-relaxed text-fg-dim">
              <strong className="text-warn">Gate C-G2 (pre-registered):</strong> {eff.benchmark.gate_C_G2.verdict}
            </p>
          )}
          <div className="mt-3 overflow-x-auto">
            <table className="w-full text-sm">
              <thead><tr className="border-b border-line text-left text-[11px] uppercase tracking-wide text-fg-faint">
                <th className="py-2 pr-3">System</th><th className="py-2 pr-3">Family</th><th className="py-2 pr-3">Locus</th>
                <th className="py-2 pr-3">Cell</th><th className="py-2 pr-3">Efficiency</th><th className="py-2">DOI</th></tr></thead>
              <tbody>
                {(eff.records || []).slice(0, 12).map((r, i) => (
                  <tr key={i} className="border-b border-line/50">
                    <td className="py-1.5 pr-3 font-mono text-xs">{r.system}</td>
                    <td className="py-1.5 pr-3 text-fg-dim">{r.family}</td>
                    <td className="py-1.5 pr-3 text-fg-dim">{r.locus}</td>
                    <td className="py-1.5 pr-3 text-fg-dim">{r.cell_type}</td>
                    <td className="py-1.5 pr-3 tabular-nums">{r.efficiency_pct == null ? "n/a" : `${r.efficiency_pct}%`}</td>
                    <td className="py-1.5 font-mono text-[10px] text-fg-faint">{r.doi}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            {(eff.records || []).length > 12 && <p className="mt-1 text-[11px] text-fg-faint">…and {eff.records.length - 12} more measured rows.</p>}
          </div>
        </Card>
      )}

      {immune?.writers?.length > 0 && (
        <Card title="Writer immunogenicity (the writer as an antigen)" icon="delivery"
              subtitle="Each genome writer's own MHC-II/CD4 epitope load and anti-drug-antibody (ADA) risk — a writer property, profiled here (it used to live in the design immune profile). Read from the committed NetMHCIIpan-4.0 cache; not recomputed.">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead><tr className="border-b border-line text-left text-[11px] uppercase tracking-wide text-fg-faint">
                <th className="py-2 pr-3">Writer</th><th className="py-2 pr-3">Family</th><th className="py-2 pr-3">Origin</th>
                <th className="py-2 pr-3">MHC-II load</th><th className="py-2 pr-3">ADA risk</th><th className="py-2">Human self-match</th></tr></thead>
              <tbody>
                {immune.writers.map((w, i) => (
                  <tr key={i} className="border-b border-line/50">
                    <td className="py-2 pr-3 font-medium">{w.representative}
                      {w.accession && <span className="ml-1 font-mono text-[10px] text-fg-faint">{w.accession}</span>}</td>
                    <td className="py-2 pr-3 text-fg-dim">{titleCase(w.writer_family)}</td>
                    <td className="py-2 pr-3"><Pill color={w.is_foreign ? "var(--warn)" : "var(--ok)"}>{w.is_foreign ? "foreign" : "self"}</Pill></td>
                    <td className="py-2 pr-3 tabular-nums">{num(w.mhc2_immune_score)}
                      <span className="text-fg-faint"> (density {num(w.epitope_density)})</span></td>
                    <td className="py-2 pr-3 tabular-nums">{num(w.ada_immune_score)}</td>
                    <td className="py-2 tabular-nums text-fg-dim">{num(w.self_match_human_proteome?.human_9mer_match_fraction)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="mt-2 text-[11px] leading-relaxed text-fg-faint">
            Scores are 0–1, higher = lower risk (1 = least presentable / least ADA-driving). {immune.method} The Cas9
            nuclease (an editor, not a large-cargo writer) and the human self control are excluded.
          </p>
        </Card>
      )}

      <Card title="Variant critique" icon="verify"
            subtitle="For a serine integrase, the measured hyperactive mutants ranked by fold-improvement over wild-type (each DOI-backed). A retrospective catalogue recovery; the blind sequence-only predictor is honestly deferred.">
        <div className="flex flex-wrap items-end gap-3">
          <Field label="Integrase / system">
            <input className="input max-w-[220px]" value={vInput} placeholder="e.g. Bxb1, PhiC31"
                   onChange={(e) => setVInput(e.target.value)}
                   onKeyDown={(e) => e.key === "Enter" && runVariants(vInput)} />
          </Field>
          <Button onClick={() => runVariants(vInput)} disabled={vBusy}>Critique variants</Button>
          <span className="pb-2 text-[11px] text-fg-faint">the frozen panel covers Bxb1 and PhiC31</span>
        </div>
        {vBusy ? <div className="mt-4"><Spinner label="Recovering the hyperactive panel…" /></div> : variants && (
          <div className="mt-4 space-y-4">
            {Object.keys(variants.hyperactive_recovery?.by_integrase || {}).length === 0 ? (
              <p className="text-sm text-fg-faint">No measured hyperactive panel for “{vInput}”. The frozen, DOI-backed
                panel currently covers <b>Bxb1</b> and <b>PhiC31</b> (serine integrases).</p>
            ) : Object.entries(variants.hyperactive_recovery.by_integrase).map(([integ, d]) => (
              <div key={integ}>
                <div className="mb-1.5 flex flex-wrap items-center gap-2 text-sm">
                  <span className="font-semibold text-fg">{integ}</span>
                  <Badge tone="ok">top: {d.top}</Badge>
                  <Badge tone={d.all_hyperactive_outrank_wt ? "ok" : "warn"}>
                    {d.all_hyperactive_outrank_wt ? "all hyperactive variants outrank WT" : "ordering not clean"}</Badge>
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead><tr className="border-b border-line text-left text-[11px] uppercase tracking-wide text-fg-faint">
                      <th className="py-2 pr-3">Variant</th><th className="py-2 pr-3">Fold vs WT</th>
                      <th className="py-2 pr-3">Basis</th><th className="py-2">DOI</th></tr></thead>
                    <tbody>
                      {(d.ranking || []).map((r, i) => {
                        const p = variants.panel?.[r.variant] || {};
                        const isWt = String(r.variant).endsWith("_WT");
                        return (
                          <tr key={i} className={`border-b border-line/50 ${isWt ? "opacity-60" : ""}`}>
                            <td className="py-1.5 pr-3 font-mono text-xs">{r.variant}{isWt && <span className="ml-1 text-fg-faint">(WT anchor)</span>}</td>
                            <td className="py-1.5 pr-3 tabular-nums font-medium text-brand">{r.fold}×</td>
                            <td className="py-1.5 pr-3 text-xs text-fg-dim">{p.basis || "n/a"}</td>
                            <td className="py-1.5 font-mono text-[10px] text-fg-faint">{p.doi || "n/a"}</td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </div>
            ))}
            {variants.blind_lm_recovery && !variants.blind_lm_recovery.available && (
              <p className="rounded-lg border border-warn/25 bg-warn/5 px-3 py-2 text-[11px] leading-relaxed text-fg-dim">
                <strong className="text-warn">Blind LM recovery deferred (no fabrication):</strong> {variants.blind_lm_recovery.note}
              </p>
            )}
          </div>
        )}
      </Card>

      {coverage && (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <Stat label="Families" value={coverage.families} />
          <Stat label="Systems" value={coverage.systems} />
          <Stat label="Measured" value={(coverage.coverage || []).reduce((a, c) => a + (c.measured || 0), 0)} color="var(--ok)" />
          <Stat label="Filter" value={family ? titleCase(family) : "all"} />
        </div>
      )}

      <Card title="Compare writers" subtitle="Every row carries its confidence; candidate reachability needs lab validation."
            right={
              <select className="input max-w-[220px]" value={family} onChange={(e) => onFamily(e.target.value)}>
                <option value="">all families ({coverage?.systems?.toLocaleString?.() || coverage?.systems})</option>
                {families.map((c) => <option key={c.family} value={c.family}>{c.family} ({(c.n || 0).toLocaleString()})</option>)}
              </select>
            }>
        <p className="mb-2 text-[11px] text-fg-faint">
          Showing {(rows || []).length} of {(total || 0).toLocaleString()} {family ? `${family} ` : ""}systems
          {!family && " — the atlas has 33,370 systems (mostly bridge_IS110 homologs); pick a family above to load its systems."}
        </p>
        <div className="overflow-x-auto">
          {tableBusy && <div className="pb-2"><Spinner label="Loading family systems…" /></div>}
          <table className="w-full text-sm">
            <thead><tr className="border-b border-line text-left text-[11px] uppercase tracking-wide text-fg-faint">
              <th className="py-2 pr-3">System</th><th className="py-2 pr-3">Family</th>
              <th className="py-2 pr-3">Confidence</th><th className="py-2 pr-3">Mechanism</th>
              <th className="py-2 pr-3">Cargo bp</th><th className="py-2 pr-3">Tier</th>
              <th className="py-2">Human activity</th></tr></thead>
            <tbody>
              {(rows || []).map((r, i) => (
                <tr key={i} className="border-b border-line/50">
                  <td className="py-2 pr-3 font-medium">{r.representative_system}</td>
                  <td className="py-2 pr-3 text-fg-dim">{r.family}</td>
                  <td className="py-2 pr-3"><Pill color={confColor[r.confidence] || "var(--muted)"}>{r.confidence}</Pill></td>
                  <td className="py-2 pr-3 text-fg-dim">{r.mechanism_bucket || "n/a"}</td>
                  <td className="py-2 pr-3 tabular-nums">{r.cargo_capacity_bp ?? "n/a"}</td>
                  <td className="py-2 pr-3">{r.reachability_tier ?? "n/a"}</td>
                  <td className="py-2 text-fg-dim">{r.human_cell_activity ?? "n/a"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="mt-3 text-[11px] text-fg-faint">{coverage?.disclaimer}</p>
      </Card>
    </div>
  );
}
