// Writer Atlas, compare genome writers across families (confidence, mechanism, cargo capacity, reachability tier,
// measured human-cell activity), AND surface the writer-efficiency work: a request-ranked recommender that
// carries a candidate learned efficiency with a trained conformal interval, the curated measured-efficiency
// dataset + the held-out Writer-Efficiency-Bench result, and the variant-critique recovery. The
// "measured vs candidate" split is explicit everywhere: the KB ranking is the grounded primary, efficiencies are
// candidate advisories (the learned model does not beat the KB baseline on held-out family at this N).
import React, { useEffect, useMemo, useState } from "react";
import WhatYouGet from "../components/WhatYouGet.jsx";
import ScoreGuide from "../components/ScoreGuide.jsx";
import { api } from "../api.js";
import { Card, Spinner, ErrorNote, Pill, Stat, Field, Select, Button, Badge, SeqWarning } from "../components/ui.jsx";
import { titleCase, num, clampInt } from "../lib/format.js";

const WRITE_TYPES = ["insertion", "knock_in_with_disruption", "landing_pad_insertion", "high_durability_insertion",
  "regulatory_element_excision", "repeat_excision", "inversion"];

// guide / att design: which families have a programmable targeting component we can design a sequence for.
const GUIDE_FAMILIES = [
  { value: "serine_integrase", label: "Serine integrase, pegRNA + attB (PASTE/PASSIGE)" },
  { value: "bridge_IS110", label: "Bridge recombinase, bridge RNA (IS110/IS621)" },
];
const GUIDE_INTEGRASES = [
  { value: "Bxb1", label: "Bxb1 (full documented attB)" },
  { value: "PhiC31", label: "PhiC31 (core only, no attB bundled)" },
];

function highlightSeq(seq, motif) {
  if (!motif || !seq.includes(motif)) return seq;
  const segs = seq.split(motif);
  const out = [];
  segs.forEach((s, i) => {
    out.push(<span key={`s${i}`}>{s}</span>);
    if (i < segs.length - 1) out.push(<mark key={`m${i}`} className="rounded bg-brand/30 px-0.5 text-fg">{motif}</mark>);
  });
  return out;
}

function SeqRow({ label, seq, highlight }) {
  if (!seq) return null;
  return (
    <div>
      <div className="flex items-center justify-between text-[11px] text-fg-faint">
        <span>{label} · {seq.length} nt</span>
        <button onClick={() => navigator.clipboard?.writeText(seq)} className="hover:text-fg">copy</button>
      </div>
      <div className="mt-0.5 break-all rounded border border-line bg-ink-900 px-2 py-1 font-mono text-[11px] text-fg-dim">
        {highlightSeq(seq, highlight)}
      </div>
    </div>
  );
}

export default function WriterAtlas() {
  const [coverage, setCoverage] = useState(null);
  const [rows, setRows] = useState(null);
  const [total, setTotal] = useState(0);       // total systems matching the current filter (server-reported)
  const [family, setFamily] = useState("");
  const [tableBusy, setTableBusy] = useState(false);
  const [busy, setBusy] = useState(true);
  const [error, setError] = useState(null);

  // Writer-efficiency surfaces
  const [eff, setEff] = useState(null);
  const [showAllRecords, setShowAllRecords] = useState(false); // "…30 more rows" -> show all 45 on demand
  const [immune, setImmune] = useState(null); // the writer's immunogenicity as an antigen (MHC-II + ADA)
  const [rec, setRec] = useState(null);
  const [recForm, setRecForm] = useState({ write_type: "insertion", cargo_bp: 2000, cell_type: "K562" });
  const [recCargoNote, setRecCargoNote] = useState(null); // "clamped to X" note when an out-of-range cargo is entered
  const [recBusy, setRecBusy] = useState(false);

  // variant critique
  const [vInput, setVInput] = useState("Bxb1");
  const [variants, setVariants] = useState(null);
  const [vBusy, setVBusy] = useState(false);

  // guide / att design
  const [gdForm, setGdForm] = useState({ writer_family: "serine_integrase", target_seq: "", donor_seq: "", integrase: "Bxb1" });
  const [gd, setGd] = useState(null);
  const [gdBusy, setGdBusy] = useState(false);
  const [gdErr, setGdErr] = useState(null);
  async function runGuide() {
    if (!gdForm.target_seq.trim()) return;
    setGdBusy(true); setGdErr(null); setGd(null);
    try { setGd(await api.guideDesign(gdForm)); } catch (e) { setGdErr(e); setGd(null); } finally { setGdBusy(false); }
  }
  const gdIsBridge = gdForm.writer_family === "bridge_IS110";

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
      <WhatYouGet
        intro="Compare genome-writing enzymes across families and get a request-ranked recommendation, with a strict, visible split between what is measured and what is a labelled candidate."
        features={[
          { name: "Writer recommender", tells: "which writer families fit your write, by KB readiness", output: "ranked 0–1 · grounded primary" },
          { name: "Predicted efficiency", tells: "a candidate learned integration efficiency + interval", output: "% + conformal interval · candidate (labelled)" },
          { name: "Measured dataset", tells: "45 DOI-backed human-cell integration efficiencies", output: "table with clickable DOIs" },
          { name: "Held-out validation", tells: "the pre-registered benchmark result, reported verbatim", output: "beats / does-not-beat baseline + CI" },
          { name: "Variant critique", tells: "does a hyperactive variant recover known activity?", output: "fold-improvement + DOI" },
          { name: "Writer immunogenicity", tells: "the enzyme's own MHC-II + ADA load as an antigen", output: "per-axis · proxy (labelled)" },
        ]}
        example="Insertion, 2000 bp, K562 → 8 families ranked by readiness (Bridge IS110 & Serine Integrase on top), each with cargo-fit and a measured/inferred confidence label; efficiency shows 'KB-only' where the model won't extrapolate."
      />
      <ScoreGuide
        intro="Compare writer families and systems for a target. Every row is either measured or a labelled candidate. The KB ranking is the grounded primary; the learned integration-efficiency is a candidate advisory with an interval, never the authoritative ranking."
        items={[
          { term: "Confidence", scale: "measured / inferred / candidate", meaning: "measured = backed by human-cell activity data; inferred = partial evidence; candidate = a knowledge-base prediction, labelled as a hypothesis." },
          { term: "Reachability tier", scale: "Tier-1 / 2 / 3", meaning: "How confidently the writer can be AIMED at an arbitrary target. Tier-1 (scannable) = a target-programmable writer whose site is found by scanning the genome (Cas9, Cas12a, bridge IS110), broadly reachable. Tier-2 (context-candidate) = reachable only in a permissive sequence/chromatin context, a candidate needing experimental confirmation. Tier-3 (not-predictable) = no reliable targeting rule yet, exploratory. Higher tier = more reach you can trust." },
          { term: "Cargo capacity", scale: "bp", meaning: "The per-family payload capacity from the curated atlas; pair it with your cargo size to see which families fit." },
          { term: "Predicted efficiency", scale: "% integration + conformal interval", meaning: "A learned predictor trained ONLY on the curated real dataset, emitted with a trained split-conformal interval. A candidate advisory, and only for families the dataset actually contains (never extrapolated to an unseen family)." },
          { term: "KB readiness", scale: "0–1, the primary rank", meaning: "A transparent score from the curated atlas (DSB-free + measured activity + cargo headroom). This, not the learned efficiency, is the grounded ranking signal." },
          { term: "Variant critique", scale: "fold over WT", meaning: "For a chosen serine integrase, the measured hyperactive mutants ranked by fold-improvement over wild-type (each DOI-backed). A retrospective catalogue recovery, a blind sequence-only predictor is deferred, not faked." },
        ]}
        caveats={[
          "Pre-registered result: the learned predictor beats the KB family-mean baseline on held-out LOCUS (CI excludes 0) but NOT on held-out FAMILY at N=42, so the KB ranking is retained as primary and the efficiency ships as a candidate.",
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
            <input className="input" type="number" min={1} max={300000} step={100} value={recForm.cargo_bp}
                   onChange={(e) => { const { value, clamped } = clampInt(e.target.value || "1", 1, 300000, 1);
                     setRecCargoNote(clamped ? `clamped to ${value.toLocaleString()} bp (allowed 1–300,000)` : null);
                     setRecForm((f) => ({ ...f, cargo_bp: value })); }} />
            {recCargoNote && <p className="mt-1 text-[11px]" style={{ color: "var(--warn)" }}>⚠ {recCargoNote}</p>}
          </Field>
          <Field label="Cell type" hint="a feature of the efficiency model (free-form)">
            <input className="input" value={recForm.cell_type}
                   onChange={(e) => setRecForm((f) => ({ ...f, cell_type: e.target.value }))} />
          </Field>
          <div className="flex items-end"><Button onClick={() => runRecommend(recForm)} loading={recBusy}>{recBusy ? "Ranking…" : "Recommend"}</Button></div>
        </div>
        {recBusy ? <div className="mt-4"><Spinner label="Ranking writers…" /></div> : rec && (
          <div className="mt-4">
            {rec.cargo_capacity_warning && (
              <p className="mb-3 rounded-lg border border-warn/40 bg-warn/10 px-3 py-2 text-[12px] leading-relaxed text-amber-200">
                <b>Cargo exceeds capacity.</b> {rec.cargo_capacity_warning}
              </p>
            )}
            {rec.write_type_note && (
              <p className="mb-3 text-[11px] leading-relaxed text-fg-faint">{rec.write_type_note}</p>
            )}
            <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead><tr className="border-b border-line text-left text-[11px] uppercase tracking-wide text-fg-faint">
                <th className="py-2 pr-3">Family</th><th className="py-2 pr-3">KB readiness</th>
                <th className="py-2 pr-3">Predicted efficiency</th><th className="py-2 pr-3">Cargo fit</th>
                <th className="py-2">Confidence</th></tr></thead>
              <tbody>
                {(rec.recommendations || []).map((r, i) => (
                  <tr key={i} className="border-b border-line/50">
                    <td className="py-2 pr-3 font-medium">{titleCase(r.family)}
                      {r.write_type_suitability === 0 && (
                        <div className="text-[10px] font-normal text-fg-faint">not the mechanism for this write</div>
                      )}</td>
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
          </div>
        )}
      </Card>

      <Card title="Guide / att design" icon="writespec"
            subtitle="Design the reprogrammable targeting component a writer needs, the bridge-RNA loops, or a pegRNA that writes a serine-integrase attB. Sequences are candidates from the published reprogramming rules (DOI-cited); a documented att is written verbatim or not at all (never fabricated).">
        <div className="grid gap-3 sm:grid-cols-4">
          <Field label="Writer family">
            <Select value={gdForm.writer_family} onChange={(v) => setGdForm((f) => ({ ...f, writer_family: v }))} options={GUIDE_FAMILIES} />
          </Field>
          <Field label={gdIsBridge ? "Target sequence" : "Target site (≥20 nt spacer)"}>
            <input className="input font-mono text-xs" placeholder="A/C/G/T…" value={gdForm.target_seq}
                   onChange={(e) => setGdForm((f) => ({ ...f, target_seq: e.target.value.toUpperCase() }))} />
            <SeqWarning seq={gdForm.target_seq} />
          </Field>
          {gdIsBridge ? (
            <Field label="Donor sequence">
              <input className="input font-mono text-xs" placeholder="A/C/G/T…" value={gdForm.donor_seq}
                     onChange={(e) => setGdForm((f) => ({ ...f, donor_seq: e.target.value.toUpperCase() }))} />
              <SeqWarning seq={gdForm.donor_seq} />
            </Field>
          ) : (
            <Field label="Integrase">
              <Select value={gdForm.integrase} onChange={(v) => setGdForm((f) => ({ ...f, integrase: v }))} options={GUIDE_INTEGRASES} />
            </Field>
          )}
          <div className="flex items-end">
            <Button onClick={runGuide} loading={gdBusy} disabled={!gdForm.target_seq.trim()}>{gdBusy ? "Designing…" : "Design guide"}</Button>
          </div>
        </div>
        {gdErr && <div className="mt-3"><ErrorNote error={gdErr} /></div>}
        {gd && (gd.available ? (
          <div className="mt-4 space-y-3 text-sm">
            <div className="flex flex-wrap items-center gap-2">
              <Badge tone="brand">{gd.design_type}</Badge>
              <Badge tone={gd.feasible ? "ok" : "warn"}>{gd.feasible ? "feasible" : "candidate, see note"}</Badge>
              <Badge tone="warn">candidate · validate empirically</Badge>
            </div>
            {gd.design_type === "pegrna_attb" ? (
              <div className="space-y-2">
                <SeqRow label="pegRNA spacer" seq={gd.design.pegrna_spacer} />
                <SeqRow label="written attB (8-bp core highlighted)" seq={gd.design.written_att} highlight="GCGGTCTC" />
                <SeqRow label="PE 3′ extension (revcomp of attB)" seq={gd.design.pe_3prime_extension} />
              </div>
            ) : (
              <div className="space-y-2">
                <SeqRow label="target-binding loop (TBL)" seq={gd.design.target_binding_loop} />
                <SeqRow label="donor-binding loop (DBL)" seq={gd.design.donor_binding_loop} />
                <p className="text-[12px]">core <span className="font-mono">{gd.design.core}</span> ·{" "}
                  {gd.design.core_matched
                    ? <span className="text-ok">matched (feasible)</span>
                    : <span className="text-bad">mismatch → infeasible (the bridge mechanism requires matching target/donor cores)</span>}</p>
              </div>
            )}
            <p className="text-[11px] leading-relaxed text-fg-faint">{gd.design.note}</p>
          </div>
        ) : (
          <p className="mt-4 text-sm text-fg-faint">{gd.reason}</p>
        ))}
      </Card>

      {eff && (
        <Card title="Measured efficiency dataset + held-out validation"
              subtitle="The curated, DOI-backed integration-efficiency dataset and the Writer-Efficiency-Bench result." icon="experiments">
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
                  : <span className="text-warn">does NOT beat baseline, CI [{num(hof?.delta?.ci95?.[0])}, {num(hof?.delta?.ci95?.[1])}] includes 0</span>}</div>
              </div>
              <div className="rounded-lg border border-line bg-ink-900 p-3 text-xs">
                <div className="font-medium text-fg">Held-out locus</div>
                <div className="mt-1 text-fg-dim">MAE {num(hol?.mae_model)} vs baseline {num(hol?.mae_baseline_family_mean)} · Spearman {num(hol?.spearman_model)}</div>
                <div className="mt-1">{hol?.delta?.model_beats_baseline
                  ? <span className="text-ok">beats baseline, CI [{num(hol?.delta?.ci95?.[0])}, {num(hol?.delta?.ci95?.[1])}] excludes 0</span>
                  : <span className="text-warn">does not beat baseline</span>}</div>
              </div>
            </div>
          )}
          {eff.benchmark?.gate_C_G2 && (
            <p className="mt-2 rounded-lg border border-warn/25 bg-warn/5 px-3 py-2 text-[11px] leading-relaxed text-fg-dim">
              <strong className="text-warn">Acceptance gate (pre-registered):</strong> {eff.benchmark.gate_C_G2.verdict}
            </p>
          )}
          <div className="mt-3 overflow-x-auto">
            <table className="w-full text-sm">
              <thead><tr className="border-b border-line text-left text-[11px] uppercase tracking-wide text-fg-faint">
                <th className="py-2 pr-3">System</th><th className="py-2 pr-3">Family</th><th className="py-2 pr-3">Locus</th>
                <th className="py-2 pr-3">Cell</th><th className="py-2 pr-3">Efficiency</th><th className="py-2">DOI</th></tr></thead>
              <tbody>
                {(eff.records || []).slice(0, showAllRecords ? undefined : 12).map((r, i) => (
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
            {(eff.records || []).length > 12 && (
              <button type="button" onClick={() => setShowAllRecords((s) => !s)}
                      className="mt-2 text-[11px] text-brand hover:underline">
                {showAllRecords ? "Show fewer" : `Show all ${eff.records.length} measured rows`}
              </button>
            )}
          </div>
        </Card>
      )}

      {immune?.writers?.length > 0 && (
        <Card title="Writer immunogenicity (the writer as an antigen)" icon="delivery"
              subtitle="Each genome writer's own MHC-II/CD4 epitope load and anti-drug-antibody (ADA) risk, a writer property, profiled here (it used to live in the design immune profile). Read from the committed NetMHCIIpan-4.0 cache; not recomputed.">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead><tr className="border-b border-line text-left text-[11px] uppercase tracking-wide text-fg-faint">
                <th className="py-2 pr-3">Writer</th><th className="py-2 pr-3">Family</th><th className="py-2 pr-3">Origin</th>
                <th className="py-2 pr-3">MHC-II load</th><th className="py-2 pr-3">ADA risk</th><th className="py-2">Human self-match</th></tr></thead>
              <tbody>
                {immune.writers.map((w, i) => (
                  <tr key={i} className={`border-b border-line/50 ${w.is_control ? "bg-ok/5" : ""}`}>
                    <td className="py-2 pr-3 font-medium">{w.representative}
                      {w.is_control && <span className="ml-1 rounded bg-ok/15 px-1 py-0.5 text-[9px] font-semibold uppercase tracking-wide text-ok">self control</span>}
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
            Scores are 0–1, higher = lower risk (1 = least presentable / least ADA-driving). {immune.method} The
            highlighted bottom row is the <b className="text-ok">human self control</b> (albumin): despite a non-zero
            MHC-II load it scores <b>ADA 1.0</b> (no ADA risk), because a self protein is <b>tolerated</b> (origin =
            self → foreignness 0). This is the reference showing <b>ADA-risk = MHC-II density × foreignness(origin)</b>
            genuinely multiplies, ADA decouples from the MHC-II load, it is not a pass-through. The Cas9 nuclease
            (an editor, not a large-cargo writer) is excluded.
          </p>
        </Card>
      )}

      <Card title="Variant critique" icon="verify"
            subtitle="For a serine integrase, the measured hyperactive mutants ranked by fold-improvement over wild-type (each DOI-backed). A retrospective catalogue recovery; the blind sequence-only predictor is deferred.">
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
          {!family && ", the atlas has 33,370 systems (mostly bridge_IS110 homologs); pick a family above to load its systems."}
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
