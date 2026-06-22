// Digital Twin, a calibrated, OOD-gated, phenotype-bounded outcome prediction. The scope discipline here is structural:
// the band is a heuristic interval that WIDENS under OOD (not a trained conformal interval, no public
// perturbation-outcome calibration set), and the structure→phenotype boundary is never crossed.
import React, { useState } from "react";
import { api } from "../api.js";
import { Card, Button, Spinner, ErrorNote, Pill, Stat, Field, Select } from "../components/ui.jsx";
import DesignForm, { DEFAULT_DESIGN, CELLS } from "../components/DesignForm.jsx";
import ConfidenceBand from "../components/ConfidenceBand.jsx";
import ImmuneProfileCard from "../components/ImmuneProfileCard.jsx";
import { num } from "../lib/format.js";

export default function Twin() {
  const [design, setDesign] = useState(DEFAULT_DESIGN);
  const [cellState, setCellState] = useState("k562");
  const [res, setRes] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);

  async function run() {
    setBusy(true); setError(null);
    try { setRes(await api.predict({ design, cell_state: cellState })); } catch (e) { setError(e); setRes(null); } finally { setBusy(false); }
  }

  const po = res?.predicted_outcome;
  const iv = res?.interval;
  const point = po?.relative_expression;
  const status = res?.extrapolating ? "extrapolating" : "grounded";

  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <Card title="Design & cell state" subtitle="The twin predicts a relative outcome conditioned on the cell state.">
        <DesignForm design={design} onChange={setDesign} />
        <div className="mt-3">
          <Field label="Cell state"><Select value={cellState} onChange={setCellState} options={CELLS} /></Field>
        </div>
        <div className="mt-4"><Button onClick={run} disabled={busy}>Predict outcome</Button></div>
      </Card>

      <Card title="Predicted outcome" subtitle="A bounded estimate, not a clinical or phenotypic guarantee.">
        {busy ? <Spinner label="Predicting…" /> : error ? <ErrorNote error={error} /> : !res ? (
          <p className="text-sm text-fg-faint">Run a prediction to see the calibrated band.</p>
        ) : (
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-2">
              <Stat label="Relative expression" value={num(point)} />
              <Stat label="OOD" value={res.extrapolating ? "yes " : "no"} color={res.extrapolating ? "var(--warn)" : "var(--ok)"} />
            </div>
            <div>
              <div className="mb-1 text-xs uppercase tracking-wide text-fg-faint">Outcome band ({po?.units})</div>
              <ConfidenceBand lo={iv?.[0]} hi={iv?.[1]} point={point} status={status} label="relative expression" />
            </div>
            <p className="rounded-lg border border-warn/25 bg-warn/5 px-3 py-2 text-[11px] leading-relaxed text-fg-dim">
              <strong className="text-warn">Interval kind.</strong> {res.interval_kind}
            </p>
            <div className="flex flex-wrap gap-2">
              {res.conditioned_on_preexisting_nab != null && <Pill>conditioned on pre-existing NAb: {String(res.conditioned_on_preexisting_nab)}</Pill>}
              {res.output_kind && <Pill>{res.output_kind}</Pill>}
              {res.no_fabrication && <Pill color="var(--ok)">no-fabrication</Pill>}
            </div>
            {res.immune_outcome?.axes && <ImmuneProfileCard profile={res.immune_outcome} />}
            <p className="text-[11px] text-fg-faint">The twin will not cross the structure→phenotype boundary: it
              estimates a relative molecular outcome, never a clinical phenotype.</p>
          </div>
        )}
      </Card>
    </div>
  );
}
