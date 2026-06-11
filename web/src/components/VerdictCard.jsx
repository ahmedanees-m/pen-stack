// VerdictCard — renders a v3.3 Verdict: legality (a hard axis) and calibrated confidence (a separate soft axis),
// never collapsed. Shows named violations with their citations, the epistemic status, and the confidence band.
import React from "react";
import ConfidenceBand from "./ConfidenceBand.jsx";
import { Pill } from "./ui.jsx";

export default function VerdictCard({ verdict }) {
  if (!verdict) return null;
  const legal = verdict.legal;
  const legalColor = legal === true ? "var(--ok)" : legal === null ? "var(--muted)" : "var(--bad)";
  const legalText = legal === true ? "Legal" : legal === null ? "Deferred" : "Illegal";
  const iv = verdict.interval;
  const conf = verdict.confidence;

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-2">
        <span className="rounded-md px-2 py-0.5 text-sm font-semibold"
              style={{ color: legalColor, background: legalColor + "1a", border: `1px solid ${legalColor}44` }}>
          {legalText}
        </span>
        <Pill>{verdict.epistemic_status}</Pill>
        {verdict.write_type && <Pill>{verdict.write_type}</Pill>}
        {verdict.no_fabrication && <Pill color="var(--ok)">no-fabrication</Pill>}
      </div>

      <div>
        <div className="mb-1 text-xs uppercase tracking-wide text-fg-faint">Calibrated confidence
          <span className="ml-1 normal-case text-fg-faint">(soft components — a separate axis from legality)</span></div>
        {conf === null || conf === undefined ? (
          <ConfidenceBand point={null} status="out_of_scope" label="confidence" />
        ) : (
          <ConfidenceBand lo={iv?.[0]} hi={iv?.[1]} point={conf}
                          status={verdict.epistemic_status?.includes("extrapolat") ? "extrapolating" : "grounded"}
                          label="confidence" />
        )}
      </div>

      {verdict.violations?.length > 0 && (
        <div>
          <div className="mb-1 text-xs uppercase tracking-wide text-bad">Violations</div>
          <ul className="space-y-1">
            {verdict.violations.map((v, i) => (
              <li key={i} className="rounded-md border border-bad/30 bg-bad/10 px-2.5 py-1.5 text-xs text-fg-dim">
                <span className="font-mono text-bad">{v.rule_id || v}</span>
                {v.message ? ` — ${v.message}` : ""}
                {v.citation ? <span className="text-fg-faint"> [{v.citation}]</span> : null}
              </li>
            ))}
          </ul>
        </div>
      )}

      {verdict.scope_flags?.length > 0 && (
        <div className="text-xs text-warn">
          Scope flags: {verdict.scope_flags.map((s) => s.id || s.title || JSON.stringify(s)).join(", ")}
        </div>
      )}
    </div>
  );
}
