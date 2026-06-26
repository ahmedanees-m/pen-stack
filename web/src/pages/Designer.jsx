// Designer, the generative designer as a verifier-as-discriminator. We submit the design GOAL; the engine plans
// real writable sites + writers (with grounded per-locus scores), sweeps the compatible delivery vehicles, screens
// each through the Guardian biosecurity gate, and returns the legal, cleared survivors with a CALIBRATED confidence
// band. Survivors are CANDIDATES, never asserted to work in vivo.
//
// v7.1.2: the page sends a GOAL (not pre-built candidates with placeholder scores), so the planner computes the
// REAL safety / durability / writer-activity per locus and the confidence band is genuinely calibrated (it differs
// by locus/vehicle, and is absent for a refused design). The Guardian screens the goal's cargo function FIRST: a
// hazardous intent (e.g. furin-cleavage tropism enhancement, dominant-negative tumor-suppressor ablation) is
// refused up front and the page shows the explicit biosecurity verdict instead of a silent empty table.
import React, { useState } from "react";
import ScoreGuide from "../components/ScoreGuide.jsx";
import { api } from "../api.js";
import { Card, Button, Spinner, ErrorNote, Pill } from "../components/ui.jsx";
import DesignForm, { DEFAULT_DESIGN } from "../components/DesignForm.jsx";
import ConfidenceBand from "../components/ConfidenceBand.jsx";
import SafetyBadge from "../components/SafetyBadge.jsx";

function goalFromDesign(base) {
  // The GOAL the engine plans + sweeps. No placeholder scores: the planner computes the grounded per-locus scores.
  return {
    gene: base.gene,
    chrom: base.chrom,
    edit_intent: base.edit_intent || "safe_harbour_insertion",
    cargo_bp: base.cargo_bp,
    cell_type: base.cell_type,
    cargo_function: base.cargo_function, // CRITICAL: the Guardian screens this for dual-use hazard signal
    in_vivo: base.in_vivo,
  };
}

export default function Designer() {
  const [design, setDesign] = useState(DEFAULT_DESIGN);
  const [res, setRes] = useState(null); // the full /generate response: {survivors, refused, safety?}
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);

  async function run() {
    setBusy(true); setError(null); setRes(null);
    try {
      const r = await api.generate({ goal: goalFromDesign(design), keep: 12, actor: "web" });
      setRes(r);
    } catch (e) { setError(e); setRes(null); } finally { setBusy(false); }
  }

  const survivors = res?.survivors || [];

  return (
    <div className="space-y-4">
      <ScoreGuide
        intro="The designer plans real writable sites for your goal, sweeps the compatible delivery vehicles, then a verifier-as-discriminator keeps only the legal, biosecurity-screened survivors. Each row is a CANDIDATE — a hypothesis that must pass verification, never asserted to work in vivo. The columns below are what survives, not a ranking claim."
        items={[
          { term: "Legal", scale: "legal / no", meaning: "The verifier's legality verdict. Only legal candidates survive; an illegal variant is discarded, never shown." },
          { term: "Safety", scale: "clear / flag / escalate / refuse", meaning: "The Guardian's biosecurity decision for this candidate. Hazardous variants are removed before they reach the frontier; a hazardous GOAL is refused up front." },
          { term: "Confidence band", scale: "0–1 + interval", meaning: "The calibrated confidence on the soft scores (not on legality, not on success), computed from the planner's per-locus safety / durability / writer-activity. The interval widens where data is thin." },
          { term: "Scope flags", scale: "count", meaning: "How many axes are out-of-scope / extrapolating for this candidate (e.g. in-vivo immune magnitude) — read them before trusting the row." },
        ]}
        caveats={[
          "An empty result is by design, not a fallback: if the goal is hazardous the Guardian refuses it up front, and if every variant was illegal or hazardous the discriminator returns nothing.",
        ]} />

      <Card title="Base design" subtitle="The designer plans real sites for the goal, sweeps vehicles, then the discriminator keeps only legal, screened survivors.">
        <DesignForm design={design} onChange={setDesign} />
        <div className="mt-4"><Button onClick={run} disabled={busy}>Generate strategies</Button></div>
      </Card>

      <Card title="Pareto survivors" subtitle="Calibrated candidates with per-locus confidence + per-design safety/immune state.">
        {busy ? <Spinner label="Discriminating…" /> : error ? <ErrorNote error={error} /> : !res ? (
          <p className="text-sm text-fg-faint">Generate to see the surviving strategies.</p>
        ) : res.refused ? (
          // The Guardian refused the GOAL up front (dual-use hazard). Show the explicit biosecurity verdict.
          <div className="rounded-lg border border-bad/40 bg-bad/5 p-4">
            <div className="flex items-center gap-2">
              <SafetyBadge decision={res.safety?.decision || "refuse"} />
              <span className="text-sm font-semibold text-bad">Guardian refused this design before scoring.</span>
            </div>
            <p className="mt-2 text-sm text-fg-dim">{res.safety?.reason || "Matches a controlled dual-use hazard signature."}</p>
            {res.safety?.hits?.length ? (
              <ul className="mt-2 space-y-1 text-[12px] text-fg-faint">
                {res.safety.hits.map((h, i) => (
                  <li key={i}>• <span className="text-fg-dim">{h.detail}</span> <Pill color="var(--bad)">{h.severity}</Pill> <span className="opacity-70">({h.kind})</span></li>
                ))}
              </ul>
            ) : null}
            <p className="mt-3 text-[11px] text-fg-faint">No protocol is emitted and no candidate is scored. This is a
              biosecurity refusal by design — the cargo function matched a controlled hazard category (DURC / HHS P3CO).
              The screen reduces, not eliminates, dual-use risk and is not a substitute for IBC review.</p>
          </div>
        ) : survivors.length === 0 ? (
          <p className="text-sm text-fg-dim">No candidates survived the discriminator. Either every swept variant was
            illegal/hazardous, or the engine found no writable plan for this gene + cell type (try a safe-harbour
            locus such as AAVS1, or a cell type with a measured atlas: K562 / HepG2 / HSPC). An empty set is by
            design, not a fallback.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-line text-left text-[11px] uppercase tracking-wide text-fg-faint">
                  <th className="py-2 pr-3">Vehicle</th>
                  <th className="py-2 pr-3">Writer</th>
                  <th className="py-2 pr-3">Cargo bp</th>
                  <th className="py-2 pr-3">Legal</th>
                  <th className="py-2 pr-3">Safety</th>
                  <th className="py-2 pr-3 w-48">Confidence</th>
                  <th className="py-2">Flags</th>
                </tr>
              </thead>
              <tbody>
                {survivors.map((s, i) => (
                  <tr key={i} className="border-b border-line/50 align-middle">
                    <td className="py-2 pr-3 font-medium">{String(s.delivery_vehicle).replace(/_/g, " ")}</td>
                    <td className="py-2 pr-3 text-fg-dim">{s.writer_family ? String(s.writer_family).replace(/_/g, " ") : "—"}</td>
                    <td className="py-2 pr-3 tabular-nums text-fg-dim">{s.cargo_bp}</td>
                    <td className="py-2 pr-3">{s.legal ? <span className="text-ok">legal</span> : <span className="text-bad">no</span>}</td>
                    <td className="py-2 pr-3"><SafetyBadge decision={s.safety_decision} compact /></td>
                    <td className="py-2 pr-3">
                      {s.confidence != null
                        ? <ConfidenceBand lo={s.interval?.[0]} hi={s.interval?.[1]} point={s.confidence} status="grounded" />
                        : <span className="text-fg-faint text-xs">not calibrated (planner scores absent)</span>}
                    </td>
                    <td className="py-2">{s.scope_flags?.length ? <Pill color="var(--warn)">{s.scope_flags.length} scope</Pill> : <span className="text-fg-faint text-xs">none</span>}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <p className="mt-3 text-[11px] text-fg-faint">Each row is a candidate the verifier judged legal and the
              Guardian cleared, with a calibrated confidence band from the planner's per-locus scores. None is a claim
              that it will work in vivo.</p>
          </div>
        )}
      </Card>
    </div>
  );
}
