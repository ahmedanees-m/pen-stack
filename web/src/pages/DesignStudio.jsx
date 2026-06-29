// Design Studio (v7.1.4): the single design surface that unifies the former Verify + Designer pages over ONE
// shared design form with two complementary actions:
//   * Verify this design   -> POST /api/verify(/proof): the 3-axis proof (legality / confidence / biosecurity),
//                             each reported separately (never collapsed), with the rule/signature that fired,
//                             its citation, and a suggested repair. Audit ONE design + learn how to fix it.
//   * Generate alternatives -> POST /api/generate: plan real sites for the GOAL, sweep the compatible delivery
//                             vehicles, and keep only the legal, biosecurity-screened survivors with a calibrated
//                             confidence band. Explore the design space for a goal.
// Generate is Verify applied to many candidates; Verify is the atomic check Generate is built on.
import React, { useState } from "react";
import { api } from "../api.js";
import { Card, Button, Spinner, ErrorNote, Pill } from "../components/ui.jsx";
import DesignForm, { DEFAULT_DESIGN } from "../components/DesignForm.jsx";
import ConfidenceBand from "../components/ConfidenceBand.jsx";
import SafetyBadge from "../components/SafetyBadge.jsx";
import ImmuneProfileCard from "../components/ImmuneProfileCard.jsx";
import ScoreGuide from "../components/ScoreGuide.jsx";

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

function goalFromDesign(b) {
  return { gene: b.gene, chrom: b.chrom, edit_intent: b.edit_intent || "safe_harbour_insertion",
           cargo_bp: b.cargo_bp, cell_type: b.cell_type, cargo_function: b.cargo_function, in_vivo: b.in_vivo };
}

export default function DesignStudio() {
  const [design, setDesign] = useState(DEFAULT_DESIGN);
  const [mode, setMode] = useState(null);   // "verify" | "generate" — which action produced the current result
  const [proof, setProof] = useState(null);
  const [verdict, setVerdict] = useState(null);
  const [gen, setGen] = useState(null);     // the /generate response
  const [busy, setBusy] = useState(null);   // "verify" | "generate" while running
  const [error, setError] = useState(null);

  async function runVerify() {
    setBusy("verify"); setError(null);
    try {
      const [p, v] = await Promise.all([api.verifyProof(design), api.verify(design)]);
      setProof(p); setVerdict(v); setMode("verify");
    } catch (e) { setError(e); } finally { setBusy(null); }
  }
  async function runGenerate() {
    setBusy("generate"); setError(null); setGen(null);
    try {
      const r = await api.generate({ goal: goalFromDesign(design), keep: 12, actor: "web" });
      setGen(r); setMode("generate");
    } catch (e) { setError(e); } finally { setBusy(null); }
  }

  const survivors = gen?.survivors || [];

  return (
    <div className="space-y-4">
      <ScoreGuide
        intro="One design surface, two actions. VERIFY audits a single design and reports three axes separately — never collapsed — with a repairable proof. GENERATE plans real sites for your goal, sweeps the compatible vehicles, and returns the legal, screened survivors with a calibrated confidence band. Generate runs the same verifier on many candidates; Verify is the single-design check it is built on."
        items={[
          { term: "Legality", scale: "pass / fail", meaning: "A grounded rule-set check: physical feasibility (reachability, payload-vs-capacity, cargo-form ↔ vehicle, integration) plus scope-of-use compliance (heritable human germline editing is out of scope and rejected). On failure it names the rule, its citation, and a repair. It does NOT adjudicate jurisdiction-specific law or IP — dual-use hazard is the separate Biosecurity axis." },
          { term: "Confidence", scale: "0–1, may abstain", meaning: "The calibrated confidence on the soft scores; it ABSTAINS rather than guess when uncalibrated. An abstain does not block — legality and biosecurity do." },
          { term: "Biosecurity", scale: "clear / flag / escalate / refuse", meaning: "The dual-use screen over function / family / taxon signatures. A refuse short-circuits the design to a human." },
          { term: "Survivors (Generate)", scale: "table", meaning: "Each row is a CANDIDATE the verifier judged legal and the Guardian cleared, with a calibrated confidence band — never a claim it works in vivo. An empty/refused result is by design." },
        ]}
        caveats={[
          "Verify passable = legality AND biosecurity pass (confidence may abstain). The verdict covers legality, feasibility and biosecurity — NOT efficacy.",
          "A flagged hazard is routed to a human, never auto-repaired.",
        ]} />

      <Card title="Design" subtitle="Build a proposed write, then Verify it (audit one design) or Generate alternatives (explore the goal).">
        <DesignForm design={design} onChange={setDesign} />
        <div className="mt-4 flex flex-wrap gap-3">
          <Button onClick={runVerify} disabled={!!busy}>{busy === "verify" ? "Verifying…" : "Verify this design"}</Button>
          <Button onClick={runGenerate} disabled={!!busy} variant="secondary">{busy === "generate" ? "Generating…" : "Generate alternatives"}</Button>
        </div>
      </Card>

      {error && <Card title="Result"><ErrorNote error={error} /></Card>}

      {/* VERIFY result: the 3-axis proof */}
      {mode === "verify" && !error && (
        <Card title="Proof" subtitle="Three axes, reported separately and never collapsed; each carries a status and, on failure, a suggested fix.">
          {busy === "verify" ? <Spinner /> : !proof ? null : (
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
      )}

      {/* GENERATE result: refused banner / survivor table / empty */}
      {mode === "generate" && !error && (
        <Card title="Candidates" subtitle="Legal, biosecurity-screened survivors with a calibrated confidence band from the planner's per-locus scores.">
          {busy === "generate" ? <Spinner label="Discriminating…" /> : !gen ? null : gen.refused ? (
            <div className="rounded-lg border border-bad/40 bg-bad/5 p-4">
              <div className="flex items-center gap-2">
                <SafetyBadge decision={gen.safety?.decision || "refuse"} />
                <span className="text-sm font-semibold text-bad">Guardian refused this design before scoring.</span>
              </div>
              <p className="mt-2 text-sm text-fg-dim">{gen.safety?.reason || "Matches a controlled dual-use hazard signature."}</p>
              {gen.safety?.hits?.length ? (
                <ul className="mt-2 space-y-1 text-[12px] text-fg-faint">
                  {gen.safety.hits.map((h, i) => (
                    <li key={i}>• <span className="text-fg-dim">{h.detail}</span> <Pill color="var(--bad)">{h.severity}</Pill> <span className="opacity-70">({h.kind})</span></li>
                  ))}
                </ul>
              ) : null}
              <p className="mt-3 text-[11px] text-fg-faint">No protocol is emitted and no candidate is scored — a biosecurity refusal by design.</p>
            </div>
          ) : survivors.length === 0 ? (
            <p className="text-sm text-fg-dim">No candidates survived. Either every swept variant was illegal/hazardous, or the engine found no writable plan for this gene + cell type (try a safe-harbour locus such as AAVS1, or a cell type with a measured atlas: K562 / HepG2 / HSPC). An empty set is by design.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-line text-left text-[11px] uppercase tracking-wide text-fg-faint">
                    <th className="py-2 pr-3">Vehicle</th><th className="py-2 pr-3">Writer</th><th className="py-2 pr-3">Cargo bp</th>
                    <th className="py-2 pr-3">Legal</th><th className="py-2 pr-3">Safety</th><th className="py-2 pr-3 w-48">Confidence</th><th className="py-2">Flags</th>
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
                          : <span className="text-fg-faint text-xs" title="This cell type has no measured writability atlas (only K562 / HepG2 / HSPC do), so the planner cannot compute calibrated scores. Legality and biosecurity still ran.">abstained · no measured atlas for this cell type</span>}
                      </td>
                      <td className="py-2">{s.scope_flags?.length ? <Pill color="var(--warn)">{s.scope_flags.length} scope</Pill> : <span className="text-fg-faint text-xs">none</span>}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <p className="mt-3 text-[11px] text-fg-faint">Each row is a candidate the verifier judged legal and the Guardian cleared, with a calibrated confidence band. None is a claim that it will work in vivo.</p>
            </div>
          )}
        </Card>
      )}

      {!mode && !error && (
        <Card title="Result"><p className="text-sm text-fg-faint">Verify a design for its 3-axis proof, or Generate alternatives to sweep the goal for legal, screened candidates.</p></Card>
      )}
    </div>
  );
}
