// Verify: submit a design and get the proof object. The three axes (legality, confidence, biosecurity) are
// reported separately, each green / amber / red, with the rule or signature that fired, its citation, and a
// suggested fix. A refused design short-circuits on biosecurity. The richer immune profile is shown alongside.
import React, { useState } from "react";
import { api } from "../api.js";
import { Card, Button, Spinner, ErrorNote } from "../components/ui.jsx";
import DesignForm, { DEFAULT_DESIGN } from "../components/DesignForm.jsx";
import ImmuneProfileCard from "../components/ImmuneProfileCard.jsx";

const AXIS_COLOR = {
  pass: "var(--ok)", clear: "var(--ok)",
  abstain: "var(--warn)", flag: "var(--warn)", escalate: "var(--warn)", deferred: "var(--warn)",
  fail: "var(--bad)", refuse: "var(--bad)",
};
const AXIS_LABEL = { legality: "Legality", confidence: "Confidence", biosecurity: "Biosecurity" };

function AxisRow({ ax }) {
  const color = AXIS_COLOR[ax.status] || "var(--muted)";
  const rep = ax.repair_hint;
  return (
    <div className="rounded border border-border p-3">
      <div className="flex items-center gap-2">
        <span style={{ width: 10, height: 10, borderRadius: 999, background: color, display: "inline-block" }} />
        <strong>{AXIS_LABEL[ax.axis] || ax.axis}</strong>
        <span className="text-xs uppercase" style={{ color }}>{ax.status}</span>
      </div>
      {ax.violated?.length > 0 && (
        <ul className="mt-2 text-sm text-fg-dim space-y-1">
          {ax.violated.map((v, i) => (
            <li key={i}>
              <code>{v.rule_id || v.signature || "signature"}</code>
              {v.reason ? `: ${v.reason}` : ""}
              {v.citation?.length ? <span className="text-fg-faint"> [{v.citation.join(", ")}]</span> : null}
            </li>
          ))}
        </ul>
      )}
      {rep?.text && (
        <p className="mt-2 text-sm">
          <span className="text-fg-faint">Suggested fix: </span>{rep.text}
          {rep.repair && <code className="ml-1">{rep.repair.field} = {String(rep.repair.set_to)}</code>}
        </p>
      )}
    </div>
  );
}

export default function Verify() {
  const [design, setDesign] = useState(DEFAULT_DESIGN);
  const [proof, setProof] = useState(null);
  const [verdict, setVerdict] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);

  async function run() {
    setBusy(true); setError(null);
    try {
      const [p, v] = await Promise.all([api.verifyProof(design), api.verify(design)]);
      setProof(p); setVerdict(v);
    } catch (e) { setError(e); setProof(null); setVerdict(null); } finally { setBusy(false); }
  }

  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <Card title="Design" subtitle="Build a proposed genomic write; the verifier evaluates each axis independently.">
        <DesignForm design={design} onChange={setDesign} />
        <div className="mt-4"><Button onClick={run} disabled={busy}>Verify design</Button></div>
      </Card>

      <Card title="Proof" subtitle="Three axes, reported separately and never collapsed; each carries a status and, on failure, a suggested fix.">
        {busy ? <Spinner /> : error ? <ErrorNote error={error} /> : !proof ? (
          <p className="text-sm text-fg-faint">Submit a design to see the proof.</p>
        ) : (
          <div className="space-y-3">
            <p className="text-sm text-fg-dim">
              Overall: {proof.passable
                ? <strong style={{ color: "var(--ok)" }}>passable</strong>
                : <strong style={{ color: "var(--bad)" }}>not passable</strong>}
              <span className="text-fg-faint"> (legality and biosecurity must pass; confidence may abstain)</span>
            </p>
            {proof.axes.map((ax) => <AxisRow key={ax.axis} ax={ax} />)}
            {verdict?.immune_profile?.axes && <ImmuneProfileCard profile={verdict.immune_profile} />}
          </div>
        )}
      </Card>
    </div>
  );
}
