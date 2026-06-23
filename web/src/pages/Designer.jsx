// Designer, the generative designer as a verifier-as-discriminator. We enumerate candidate vehicles × cargo for
// a base design, submit them, and the engine DISCARDS the illegal/hazardous and returns calibrated, immune-
// profiled survivors on the safety/efficacy frontier. Survivors are CANDIDATES, never asserted to work.
import React, { useState } from "react";
import ScoreGuide from "../components/ScoreGuide.jsx";
import { api } from "../api.js";
import { Card, Button, Spinner, ErrorNote, Pill } from "../components/ui.jsx";
import DesignForm, { DEFAULT_DESIGN, VEHICLES } from "../components/DesignForm.jsx";
import ConfidenceBand from "../components/ConfidenceBand.jsx";
import SafetyBadge from "../components/SafetyBadge.jsx";
import { num } from "../lib/format.js";

function buildCandidates(base) {
  const out = [];
  for (const veh of VEHICLES) {
    for (const bp of [base.cargo_bp, Math.round(base.cargo_bp * 1.5)]) {
      out.push({ ...base, delivery_vehicle: veh, cargo_bp: bp,
        safety: 0.7, p_durable: 0.6, writer_activity: 0.5, on_target: 0.8, deliverability: 0.6 });
    }
  }
  return out;
}

export default function Designer() {
  const [design, setDesign] = useState(DEFAULT_DESIGN);
  const [res, setRes] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);

  async function run() {
    setBusy(true); setError(null);
    try {
      const r = await api.generate({ candidates: buildCandidates(design), keep: 12, actor: "web" });
      setRes(r.survivors || r);
    } catch (e) { setError(e); setRes(null); } finally { setBusy(false); }
  }

  return (
    <div className="space-y-4">
      <ScoreGuide
        intro="The designer sweeps vehicles × cargo, then a verifier-as-discriminator keeps only the legal, screened survivors. Each row is a CANDIDATE — a hypothesis that must pass verification, never asserted to work in vivo. The columns below are what survives, not a ranking claim."
        items={[
          { term: "Legal", scale: "legal / no", meaning: "The verifier's legality verdict. Only legal candidates survive; an illegal variant is discarded, never shown." },
          { term: "Safety", scale: "clear / flag / escalate / refuse", meaning: "The Guardian's biosecurity decision for this candidate. Hazardous variants are removed before they reach the frontier." },
          { term: "Confidence band", scale: "0–1 + interval", meaning: "The calibrated confidence on the soft scores (not on legality, not on success). The interval widens where data is thin." },
          { term: "Scope flags", scale: "count", meaning: "How many axes are out-of-scope / extrapolating for this candidate (e.g. in-vivo immune magnitude) — read them before trusting the row." },
        ]}
        caveats={[
          "An empty result is by design, not a fallback: if every variant was illegal or hazardous, the discriminator returns nothing.",
        ]} />

      <Card title="Base design" subtitle="The designer sweeps vehicles × cargo, then the discriminator keeps only legal, screened survivors.">
        <DesignForm design={design} onChange={setDesign} />
        <div className="mt-4"><Button onClick={run} disabled={busy}>Generate strategies</Button></div>
      </Card>

      <Card title="Pareto survivors" subtitle="Ranked candidates with calibrated confidence + per-design safety/immune state.">
        {busy ? <Spinner label="Discriminating…" /> : error ? <ErrorNote error={error} /> : !res ? (
          <p className="text-sm text-fg-faint">Generate to see the surviving strategies.</p>
        ) : res.length === 0 ? (
          <p className="text-sm text-fg-dim">No candidates survived the discriminator, every variant was illegal or
            hazardous. That is an empty set by design, not a fallback.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-line text-left text-[11px] uppercase tracking-wide text-fg-faint">
                  <th className="py-2 pr-3">Vehicle</th>
                  <th className="py-2 pr-3">Cargo bp</th>
                  <th className="py-2 pr-3">Legal</th>
                  <th className="py-2 pr-3">Safety</th>
                  <th className="py-2 pr-3 w-48">Confidence</th>
                  <th className="py-2">Flags</th>
                </tr>
              </thead>
              <tbody>
                {res.map((s, i) => (
                  <tr key={i} className="border-b border-line/50 align-middle">
                    <td className="py-2 pr-3 font-medium">{String(s.delivery_vehicle).replace(/_/g, " ")}</td>
                    <td className="py-2 pr-3 tabular-nums text-fg-dim">{s.cargo_bp}</td>
                    <td className="py-2 pr-3">{s.legal ? <span className="text-ok">legal</span> : <span className="text-bad">no</span>}</td>
                    <td className="py-2 pr-3"><SafetyBadge decision={s.safety_decision} compact /></td>
                    <td className="py-2 pr-3"><ConfidenceBand lo={s.interval?.[0]} hi={s.interval?.[1]} point={s.confidence} status="grounded" /></td>
                    <td className="py-2">{s.scope_flags?.length ? <Pill color="var(--warn)">{s.scope_flags.length} scope</Pill> : <span className="text-fg-faint text-xs">none</span>}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <p className="mt-3 text-[11px] text-fg-faint">Each row is a candidate the verifier judged legal and the
              Guardian cleared, with a calibrated confidence band. None is a claim that it will work in vivo.</p>
          </div>
        )}
      </Card>
    </div>
  );
}
