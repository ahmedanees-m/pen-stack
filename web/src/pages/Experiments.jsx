// Experiments, the next-experiment designer. Given a pool of candidate designs, the engine ranks a diverse,
// informative batch by expected information gain (active learning), what to run next to learn the most.
import React, { useState } from "react";
import WhatYouGet from "../components/WhatYouGet.jsx";
import ScoreGuide from "../components/ScoreGuide.jsx";
import { api } from "../api.js";
import { Card, Button, Spinner, ErrorNote, Field, Select } from "../components/ui.jsx";
import DesignForm, { DEFAULT_DESIGN, CELLS } from "../components/DesignForm.jsx";
import { num } from "../lib/format.js";

// The candidate pool spans the facets that actually drive INFORMATIVENESS: cell type (an unmeasured cell type is
// more informative to run, coverage novelty) × a diverse set of delivery vehicles (different in-scope immune axes
// to validate + different capacities → feasibility). A pool that only varied vehicle × cargo at ONE cell type gave
// a near-constant score, because relative expression is per-copy and the twin's interval is a fixed band; spanning
// cell types is what lets the acquisition differentiate experiments. The vehicle set is kept to 4 diverse modalities
// (viral / integrating / LNP / physical) so the pool (7×4=28) stays responsive; the user's cargo size is honoured
// (a large cargo makes the small-capacity vehicles infeasible, the feasibility signal).
const POOL_VEHICLES = ["AAV_single", "lentivirus", "lnp_mrna", "electroporation"];
function poolFrom(base) {
  const out = [];
  for (const cell of CELLS) {
    for (const veh of POOL_VEHICLES) {
      out.push({ ...base, cell_type: cell, delivery_vehicle: veh, cargo_bp: base.cargo_bp || 3000 });
    }
  }
  return out;
}

export default function Experiments() {
  const [design, setDesign] = useState(DEFAULT_DESIGN);
  const [k, setK] = useState(6);
  const [res, setRes] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);

  async function run() {
    setBusy(true); setError(null);
    try {
      // cell_state is left empty: the pool spans cell types, so each candidate is scored in ITS OWN cell type
      // (coverage novelty varies) rather than being collapsed to one global context.
      const r = await api.suggest({ candidates: poolFrom(design), cell_state: "", k });
      setRes(r.batch || r);
    } catch (e) { setError(e); setRes(null); } finally { setBusy(false); }
  }

  const maxMarginal = res?.length ? Math.max(...res.map((d) => d.marginal_gain ?? d.expected_info_gain ?? 0), 1e-6) : 1;

  const [camp, setCamp] = useState(null);
  const [campBusy, setCampBusy] = useState(false);
  async function loadCampaign() {
    setCampBusy(true);
    try { setCamp(await api.campaign()); } catch { setCamp(null); } finally { setCampBusy(false); }
  }

  return (
    <div className="space-y-4">
      <WhatYouGet
        intro="Decide what to test next: a diverse batch of candidate experiments, spanning cell types and delivery vehicles, ranked by how much each would actually teach you, plus an executable validation campaign that targets the platform's first outcome-validated axis."
        features={[
          { name: "Next-experiment batch", tells: "which measurements teach the most, given the rest of the batch", output: "ranked by marginal information gain (diminishing returns)" },
          { name: "Why it ranks", tells: "the real signals behind each pick", output: "coverage novelty · immune value-of-information · buildability" },
          { name: "Validation campaign", tells: "a concrete cassette × locus × cell-type plan to run", output: "an executable experiment specification" },
        ]}
        example="For an expression design across 7 cell types × 4 vehicles → the engine ranks experiments in UNMEASURED cell types (no data yet) and buildable vehicles highest, and spreads the batch so each pick adds new information, not 6 copies of the same regime."
      />
      <ScoreGuide
        intro="The most-informative next experiments, and the validation campaign that targets the program's first outcome-validated axis. Experiments are candidates; the wet run is the standing bottleneck."
        items={[
          { term: "Marginal gain", scale: "higher = more informative now", meaning: "The submodular active-learning value: an experiment's intrinsic informativeness MINUS its overlap with the experiments already scheduled above it. It decreases down the batch (diminishing returns), the per-experiment signal, not a fixed number." },
          { term: "Expected info gain (EIG)", scale: "reducible uncertainty", meaning: "The model's reducible predictive uncertainty for this experiment. It is HIGHER in an unmeasured cell type (no atlas data there yet) and out-of-distribution designs, and the same across gene/vehicle/cargo in a measured cell, the mechanistic twin genuinely has no per-gene uncertainty, so a flat value there is by design, not stuck." },
          { term: "Immune value-of-information", scale: "count of axes", meaning: "How many still-proxy immune axes this experiment could turn into outcome-validated ones, i.e. how many are IN SCOPE to measure (a PEGylated LNP puts anti-PEG in scope; AAV does not). It counts validat-ABILITY, so it does not change with e.g. CpG content, that drives the innate axis SCORE on the Twin page, a different quantity." },
          { term: "Validation campaign", scale: "ordered batch", meaning: "A fixed, pre-registered (cassette × locus × cell type) plan targeting the calibrate_axis gate, independent of the candidate-pool form above; identical on repeat by design." },
        ]}
        caveats={[
          "Within one regime (same cell-type coverage, same buildability) the mechanistic twin cannot finely rank experiments, the ordering there is diversity + immune-VOI. Coverage, buildability and OOD are what move the headline EIG.",
          "EIG-beats-random is reported verbatim either way (it is rep-sensitive on the synthetic task); cloud-lab execution is mock / dry-run.",
        ]} />

    <div className="grid gap-4 lg:grid-cols-2">
      <Card title="Candidate pool" subtitle="Your design, explored across every cell type × 4 diverse vehicles; the engine ranks the most informative batch.">
        <DesignForm design={design} onChange={setDesign} showCargoFunction={false} />
        <div className="mt-3 grid grid-cols-2 gap-3">
          <Field label="Batch size (k)">
            <Select value={String(k)} onChange={(v) => setK(parseInt(v, 10))} options={["3", "6", "8", "12"]} />
          </Field>
        </div>
        <p className="mt-2 text-[11px] text-fg-faint">The pool spans all {CELLS.length} cell types × {POOL_VEHICLES.length} vehicles
          ({POOL_VEHICLES.map((v) => v.replace(/_/g, " ")).join(", ")}) at your cargo size, so the ranking reflects real
          coverage, buildability and immune-validation differences, not one fixed cell.</p>
        <div className="mt-4"><Button onClick={run} disabled={busy}>Suggest experiments</Button></div>
      </Card>

      <Card title="Next-experiment batch" subtitle="Ranked by marginal information gain, diverse, buildable, and pointed at under-characterised regimes.">
        {busy ? <Spinner label="Ranking by information gain…" /> : error ? <ErrorNote error={error} /> : !res ? (
          <p className="text-sm text-fg-faint">Suggest a batch to see what to run next.</p>
        ) : (
          <ol className="space-y-2">
            {res.map((d, i) => {
              const mg = d.marginal_gain ?? d.expected_info_gain ?? 0;
              const cov = d.coverage_novelty;
              const covTag = cov >= 1 ? "unmeasured cell, high novelty" : cov > 0 ? "partial-atlas cell" : "measured cell";
              return (
              <li key={i} className="rounded-lg border border-line bg-ink-900 p-3">
                <div className="flex items-center justify-between gap-2">
                  <span className="text-sm font-medium">{i + 1}. {String(d.delivery_vehicle).replace(/_/g, " ")} · {String(d.cell_type)} · {d.cargo_bp} bp</span>
                  <span className="text-xs tabular-nums text-brand" title="marginal information gain given the picks above">gain {num(mg, 3)}</span>
                </div>
                <div className="mt-1.5 h-1.5 rounded-full bg-ink-800">
                  <div className="h-full rounded-full bg-brand/70" style={{ width: `${Math.max(4, (mg / maxMarginal) * 100)}%` }} />
                </div>
                <div className="mt-1.5 flex flex-wrap gap-x-3 gap-y-0.5 text-[10px] text-fg-faint">
                  <span>{covTag}</span>
                  {d.immune_voi != null && <span>immune-VOI {num(d.immune_voi, 0)}</span>}
                  {d.expected_info_gain != null && <span>EIG {num(d.expected_info_gain, 3)}</span>}
                  {d.buildable === false && <span style={{ color: "var(--warn)" }}>not buildable, down-weighted</span>}
                </div>
              </li>
              );
            })}
          </ol>
        )}
      </Card>
    </div>

      <Card title="Validation campaign (v7.0)" subtitle="The first campaign that points active learning at the measurements which would earn the program's first outcome-validated axis. A candidate plan, not a result; the wet run is the standing bottleneck.">
        <Button onClick={loadCampaign} disabled={campBusy}>Load expression-validation campaign</Button>
        {campBusy && <div className="mt-3"><Spinner label="Designing the campaign…" /></div>}
        {camp && (
          <div className="mt-3 space-y-3 text-sm">
            <p className="text-fg-dim">Targets <code>{camp.target_gate?.gate}</code> for the <b>{camp.target_gate?.axis}</b> axis ({camp.target_gate?.current}). {camp.n_candidates} candidate measurements; Level {camp.autonomy_level}, human in control.</p>
            <p className="text-[11px] text-fg-faint">EIG beats random on the acquisition order: <b>{String(camp.eig_beats_random)}</b> (curve-area gap {JSON.stringify(camp.active_vs_random?.ci)}), reported either way.</p>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead><tr className="border-b border-line text-left text-[11px] uppercase tracking-wide text-fg-faint">
                  <th className="py-2 pr-3">#</th><th className="py-2 pr-3">Cassette</th><th className="py-2 pr-3">Locus</th><th className="py-2 pr-3">Cell</th><th className="py-2">EIG</th></tr></thead>
                <tbody>
                  {(camp.batch || []).map((b, i) => (
                    <tr key={i} className="border-b border-line/50">
                      <td className="py-1.5 pr-3 tabular-nums">{i + 1}</td>
                      <td className="py-1.5 pr-3 font-mono text-xs">{b.cassette}</td>
                      <td className="py-1.5 pr-3">{b.locus}</td>
                      <td className="py-1.5 pr-3">{b.cell}</td>
                      <td className="py-1.5 tabular-nums text-brand">{num(b.expected_info_gain, 3)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p className="text-[11px] text-amber-300/80">{camp.note}</p>
          </div>
        )}
      </Card>
    </div>
  );
}
