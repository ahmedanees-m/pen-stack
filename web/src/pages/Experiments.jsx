// Experiments, the next-experiment designer. Given a pool of candidate designs, the engine ranks a diverse,
// informative batch by expected information gain (active learning), what to run next to learn the most.
import React, { useState } from "react";
import ScoreGuide from "../components/ScoreGuide.jsx";
import { api } from "../api.js";
import { Card, Button, Spinner, ErrorNote, Field, Select } from "../components/ui.jsx";
import DesignForm, { DEFAULT_DESIGN, VEHICLES, CELLS } from "../components/DesignForm.jsx";
import { num } from "../lib/format.js";

function poolFrom(base) {
  const out = [];
  for (const veh of VEHICLES) {
    for (const bp of [2000, 3500, 5000]) {
      out.push({ ...base, delivery_vehicle: veh, cargo_bp: bp });
    }
  }
  return out;
}

export default function Experiments() {
  const [design, setDesign] = useState(DEFAULT_DESIGN);
  const [cellState, setCellState] = useState("k562");
  const [k, setK] = useState(6);
  const [res, setRes] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);

  async function run() {
    setBusy(true); setError(null);
    try {
      const r = await api.suggest({ candidates: poolFrom(design), cell_state: cellState, k });
      setRes(r.batch || r);
    } catch (e) { setError(e); setRes(null); } finally { setBusy(false); }
  }

  const maxEig = res?.length ? Math.max(...res.map((d) => d.expected_info_gain || 0)) : 1;

  const [camp, setCamp] = useState(null);
  const [campBusy, setCampBusy] = useState(false);
  async function loadCampaign() {
    setCampBusy(true);
    try { setCamp(await api.campaign()); } catch { setCamp(null); } finally { setCampBusy(false); }
  }

  return (
    <div className="space-y-4">
      <ScoreGuide
        intro="The most-informative next experiments, and the validation campaign that targets the program's first outcome-validated axis. Experiments are candidates; the wet run is the standing bottleneck."
        items={[
          { term: "Expected info gain (EIG)", scale: "higher = more informative", meaning: "How much an experiment is expected to reduce the model's predictive uncertainty (+ immune value-of-information). The batch is greedy-diverse." },
          { term: "Validation campaign", scale: "ordered batch", meaning: "The (cassette × locus × cell type) measurements ordered by EIG that would flip the calibrate_axis gate to outcome-validated." },
        ]}
        caveats={[
          "EIG-beats-random is reported verbatim either way (it is rep-sensitive on the synthetic task); cloud-lab execution is mock / dry-run.",
        ]} />

    <div className="grid gap-4 lg:grid-cols-2">
      <Card title="Candidate pool" subtitle="A grid of vehicles × cargo; the engine picks the most informative batch.">
        <DesignForm design={design} onChange={setDesign} showCargoFunction={false} />
        <div className="mt-3 grid grid-cols-2 gap-3">
          <Field label="Cell state"><Select value={cellState} onChange={setCellState} options={CELLS} /></Field>
          <Field label="Batch size (k)">
            <Select value={String(k)} onChange={(v) => setK(parseInt(v, 10))} options={["3", "6", "8", "12"]} />
          </Field>
        </div>
        <div className="mt-4"><Button onClick={run} disabled={busy}>Suggest experiments</Button></div>
      </Card>

      <Card title="Next-experiment batch" subtitle="Ranked by expected information gain, diverse and informative.">
        {busy ? <Spinner label="Ranking by information gain…" /> : error ? <ErrorNote error={error} /> : !res ? (
          <p className="text-sm text-fg-faint">Suggest a batch to see what to run next.</p>
        ) : (
          <ol className="space-y-2">
            {res.map((d, i) => (
              <li key={i} className="rounded-lg border border-line bg-ink-900 p-3">
                <div className="flex items-center justify-between gap-2">
                  <span className="text-sm font-medium">{i + 1}. {String(d.delivery_vehicle).replace(/_/g, " ")} · {d.cargo_bp} bp</span>
                  <span className="text-xs tabular-nums text-brand">EIG {num(d.expected_info_gain, 3)}</span>
                </div>
                <div className="mt-1.5 h-1.5 rounded-full bg-ink-800">
                  <div className="h-full rounded-full bg-brand/70" style={{ width: `${Math.max(4, (d.expected_info_gain / maxEig) * 100)}%` }} />
                </div>
              </li>
            ))}
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
