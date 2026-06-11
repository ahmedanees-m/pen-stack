// Experiments — the next-experiment designer. Given a pool of candidate designs, the engine ranks a diverse,
// informative batch by expected information gain (active learning) — what to run next to learn the most.
import React, { useState } from "react";
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

  return (
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

      <Card title="Next-experiment batch" subtitle="Ranked by expected information gain — diverse and informative.">
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
  );
}
