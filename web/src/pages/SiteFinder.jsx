// Site Finder: score loci for a gene by safety + durability -> writability, and rank concrete write plans for an
// edit intent. Atlas-dependent: only cell types with a measured writability atlas return loci (the rest are a
// data-gated roadmap, shown but disabled). Cargo size + edit intent shape the ranked PLANS, not the per-locus
// writability (which is intrinsic to the gene x cell-type context) - the UI says so explicitly.
import React, { useEffect, useState } from "react";
import { api } from "../api.js";
import { Card, Button, Spinner, ErrorNote, Field, Badge } from "../components/ui.jsx";
import ScoreGuide from "../components/ScoreGuide.jsx";
import { INTENTS } from "../components/DesignForm.jsx";
import ConfidenceBand from "../components/ConfidenceBand.jsx";
import { num } from "../lib/format.js";

const CARGO_MAX = 200000;
// fallback if /api/celltypes is unreachable (keeps the page honest about coverage either way)
const FALLBACK_CELLS = [
  { id: "k562", label: "K562", measured: true, coverage: "full" },
  { id: "hepg2", label: "HepG2", measured: true, coverage: "full" },
  { id: "hspc", label: "HSPC", measured: true, coverage: "partial" },
  { id: "h1_hesc", label: "H1 hESC", measured: false, coverage: "none" },
  { id: "ipsc", label: "iPSC", measured: false, coverage: "none" },
  { id: "cd8_t", label: "CD8 T", measured: false, coverage: "none" },
  { id: "pbmc", label: "PBMC", measured: false, coverage: "none" },
];
const COV_TONE = { full: "ok", partial: "warn", none: "neutral" };

export default function SiteFinder() {
  const [gene, setGene] = useState("CCR5");
  const [ct, setCt] = useState("k562");
  const [intent, setIntent] = useState("safe_harbour_insertion");
  const [cargo, setCargo] = useState(2000);
  const [cells, setCells] = useState(FALLBACK_CELLS);
  const [result, setResult] = useState(null); // { gene, ct, ctLabel } captured at score time -> stable headers
  const [loci, setLoci] = useState(null);
  const [plans, setPlans] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => { api.celltypes().then((r) => r?.cell_types?.length && setCells(r.cell_types)).catch(() => {}); }, []);

  const measured = cells.filter((c) => c.measured);
  const roadmap = cells.filter((c) => !c.measured);
  const selected = cells.find((c) => c.id === ct) || measured[0];
  const geneOk = gene.trim().length > 0;

  function setCargoSafe(v) {
    const n = parseInt(v || "0", 10);
    setCargo(Number.isNaN(n) ? 0 : Math.min(CARGO_MAX, Math.max(0, n)));
  }

  async function run() {
    if (!geneOk) return;
    setBusy(true); setError(null); setLoci(null); setPlans(null);
    const scored = { gene: gene.trim(), ct, ctLabel: selected?.label || ct };
    try {
      const [w, p] = await Promise.allSettled([
        api.writable(scored.gene, ct, 20),
        api.plan(scored.gene, intent, cargo, ct, 6),
      ]);
      if (w.status === "fulfilled") setLoci(w.value.loci || []);
      if (p.status === "fulfilled") setPlans(p.value.plans || []);
      if (w.status === "rejected" && p.status === "rejected") throw w.reason;
      setResult(scored);
    } catch (e) { setError(e); } finally { setBusy(false); }
  }

  return (
    <div className="space-y-4">
      <Card title="Find writable sites" subtitle="Loci scored by safety and durability for a target gene in a chosen cell type.">
        <div className="grid gap-3 sm:grid-cols-4">
          <Field label="Gene" hint={!geneOk ? "Enter a gene symbol (e.g. CCR5, AAVS1, F8)." : undefined}>
            <input className={`input ${!geneOk ? "border-bad/60" : ""}`} value={gene} placeholder="e.g. CCR5"
                   onChange={(e) => setGene(e.target.value)} />
          </Field>
          <Field label="Cell type" hint={selected ? selected.coverage + " coverage" : undefined}>
            <select className="input" value={ct} onChange={(e) => setCt(e.target.value)}>
              <optgroup label="Measured (real writability atlas)">
                {measured.map((c) => <option key={c.id} value={c.id}>{c.label} · {c.coverage}</option>)}
              </optgroup>
              {roadmap.length > 0 && (
                <optgroup label="Roadmap · data-gated (no atlas yet)">
                  {roadmap.map((c) => <option key={c.id} value={c.id} disabled>{c.label} · not available</option>)}
                </optgroup>
              )}
            </select>
          </Field>
          <Field label="Edit intent" hint="shapes the ranked plans below">
            <select className="input" value={intent} onChange={(e) => setIntent(e.target.value)}>
              {INTENTS.map((v) => <option key={v} value={v}>{v.replace(/_/g, " ")}</option>)}
            </select>
          </Field>
          <Field label="Cargo bp" hint="for the ranked plans (capacity/delivery)">
            <input className="input" type="number" min={0} max={CARGO_MAX} step={100} value={cargo}
                   onChange={(e) => setCargoSafe(e.target.value)} />
          </Field>
        </div>
        <div className="mt-4 flex items-center gap-3">
          <Button onClick={run} disabled={busy || !geneOk}>Score sites</Button>
          {selected && <Badge tone={COV_TONE[selected.coverage]}>{selected.label}: {selected.coverage} coverage</Badge>}
        </div>
        <p className="mt-3 text-[11px] leading-relaxed text-fg-faint">
          The loci table is the intrinsic per-locus writability for <b>gene × cell type</b> — it does not change with
          cargo size or edit intent. <b>Cargo bp</b> and <b>edit intent</b> shape the <b>ranked write plans</b> below
          (which writer fits, capacity, delivery). Only cell types with a measured atlas return loci.
        </p>
      </Card>

      <ScoreGuide
        defaultOpen
        intro="Every locus is a 1-kb genomic bin. Each score is 0–1, higher is better. They are relative, calibrated estimates for decision-support, not guarantees: 1.0 means 'top of the modeled range', not 'perfect' or 'proven'."
        items={[
          { term: "Safety", scale: "0–1, higher = safer", meaning: "1 − P(genotoxic) from a model over chromatin marks + log-distance to the nearest oncogene (CancerMine), tumour-suppressor, essential gene (DepMap) and TSS, plus retroviral (MLV) integration density. ~1.0 = far from cancer/essential genes; low = near one (e.g. LMO2, MECOM)." },
          { term: "Durability", scale: "0–1, higher = lasts", meaning: "P(durable) = 1 − P(silenced), from a TRIP-trained chromatin model (thousands of genome-integrated reporters scored for positional silencing), applied to this cell type's histone marks. The slider shows the modeled probability an insert here keeps expressing." },
          { term: "Writability", scale: "0–1, the headline", meaning: "0.5·Safety + 0.5·Durability — a documented 50/50 blend, not a product. A 0.92 might be 'very safe, decent durability' or the reverse; the two columns tell you which trade-off you are getting." },
        ]}
        caveats={[
          "Validation: the learned writability separates curated safe harbours (AAVS1, CCR5, CLYBL…) from matched controls at AUROC 0.68 (95% CI 0.54–0.83, N=16) — modest, above chance. Naive distance rules fail this (AUROC ~0.51) because real safe harbours sit inside genes.",
          "Durability is trained on mouse TRIP and transferred to human; partial-coverage cell types degrade gracefully and are labelled, never silently extrapolated.",
          "A locus's writability is intrinsic to the gene × cell-type context. Cargo size and edit intent are properties of the strategy, so they shape the ranked plans, not the per-locus score.",
        ]}
      />

      {busy && <Card><Spinner label="Scanning the writability atlas…" /></Card>}
      {error && <Card><ErrorNote error={error} /></Card>}

      {loci && result && (
        <Card title={`Writable loci for ${result.gene}`}
              subtitle={`${loci.length} candidate loci · ${result.ctLabel}`}>
          {loci.length === 0 ? (
            <p className="text-sm text-fg-faint">No loci returned for {result.gene} in {result.ctLabel}. The gene may
              be unrecognized, or this cell type has no measured atlas.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead><tr className="border-b border-line text-left text-[11px] uppercase tracking-wide text-fg-faint">
                  <th className="py-2 pr-3">Locus</th><th className="py-2 pr-3">Safety</th>
                  <th className="py-2 pr-3 w-44">Durability</th><th className="py-2">Writability</th></tr></thead>
                <tbody>
                  {loci.map((l, i) => (
                    <tr key={i} className="border-b border-line/50">
                      <td className="py-2 pr-3 font-mono text-xs">{l.chrom}:bin{l.bin}</td>
                      <td className="py-2 pr-3 tabular-nums">{num(l.safety)}</td>
                      <td className="py-2 pr-3"><ConfidenceBand point={l.p_durable} status="grounded" /></td>
                      <td className="py-2 tabular-nums font-medium text-brand">{num(l.writability)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>
      )}

      {plans && result && (
        <Card title="Ranked write plans" subtitle={`Traceable plans for "${intent.replace(/_/g, " ")}" · cargo ${cargo} bp · ${result.ctLabel}`}>
          {plans.length === 0 ? <p className="text-sm text-fg-faint">No plans returned.</p> : (
            <ol className="space-y-2">
              {plans.map((p, i) => (
                <li key={i} className="rounded-lg border border-line bg-ink-900 p-3 text-sm">
                  <div className="flex items-center justify-between">
                    <span className="font-medium">{i + 1}. {p.writer} → {p.site?.chrom}:bin{p.site?.bin}</span>
                    <span className="text-xs tabular-nums text-brand">score {num(p.score)}</span>
                  </div>
                  <div className="mt-1 flex flex-wrap gap-3 text-[11px] text-fg-dim">
                    <span>safety {num(p.safety)}</span><span>durability {num(p.durability)}</span>
                    <span>writer activity {num(p.writer_activity)}</span><span>on-target {num(p.on_target)}</span>
                    {p.reachability_tier && <span>tier {p.reachability_tier}</span>}
                  </div>
                </li>
              ))}
            </ol>
          )}
        </Card>
      )}
    </div>
  );
}
