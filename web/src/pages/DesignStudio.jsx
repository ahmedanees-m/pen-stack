// Design Studio: the single design surface that unifies the former Verify + Designer pages over ONE
// shared design form with two complementary actions:
//   * Verify this design   -> POST /api/verify(/proof): the 3-axis proof (legality / confidence / biosecurity),
//                             each reported separately (never collapsed), with the rule/signature that fired,
//                             its citation, and a suggested repair. Audit ONE design + learn how to fix it.
//   * Generate alternatives -> POST /api/generate: plan real sites for the GOAL, sweep the compatible delivery
//                             vehicles, and keep only the legal, biosecurity-screened survivors with a calibrated
//                             confidence band. Explore the design space for a goal.
// Generate is Verify applied to many candidates; Verify is the atomic check Generate is built on.
import React, { useState, useEffect } from "react";
import WhatYouGet from "../components/WhatYouGet.jsx";
import { api } from "../api.js";
import { Card, Button, Spinner, ErrorNote, Pill, Select } from "../components/ui.jsx";
import DesignForm, { DEFAULT_DESIGN, VEHICLES, CHROMS } from "../components/DesignForm.jsx";
import { clampInt } from "../lib/format.js";
import ConfidenceBand from "../components/ConfidenceBand.jsx";
import SafetyBadge from "../components/SafetyBadge.jsx";
import ImmuneProfileCard from "../components/ImmuneProfileCard.jsx";
import ScopeLedger from "../components/ScopeLedger.jsx";
import ScoreGuide from "../components/ScoreGuide.jsx";

// The five-axis immune-risk guide, folded in from the former Delivery & Immunity page: one design surface
// covers Verify / Generate AND the per-axis immune profile, so there is no separate delivery page to keep in sync.
const IMMUNE_GUIDE = {
  intro: "This is the DELIVERY immune profile: the vehicle/cargo axes, reported SEPARATELY (0–1, higher = lower risk), never collapsed into one number. Each is a mechanistic or population proxy, not a patient-specific prediction. An axis that lacks its input abstains and shows n/a, never a guessed value, supply a cargo sequence (innate) or a PEGylated vehicle (anti-PEG) to compute it. The WRITER enzyme's own immunogenicity (MHC-II + ADA) lives on the Writer Atlas page, where the writer is chosen.",
  items: [
    { term: "Genotoxicity", scale: "higher = safer", meaning: "1.0 = episomal / non-integrating (no insertional-oncogenesis mechanism); lower = an integrating vector enriched for integrations near oncogenes." },
    { term: "CD8 epitope", scale: "higher = less visible", meaning: "1 − fraction of the capsid presentable to cytotoxic T cells over a frequent HLA-I panel (NetMHCpan-4.1, MHCflurry cross-check). Sequence-intrinsic, CD8/MHC-I only." },
    { term: "Innate sensing", scale: "higher = lower load", meaning: "CpG/TLR9 for DNA cargo, U-content + dsRNA (ViennaRNA) for mRNA. The cargo form follows the vehicle. Needs a cargo sequence; abstains without one." },
    { term: "Pre-existing NAb / anti-PEG", scale: "higher = lower barrier", meaning: "Pre-existing neutralizing-antibody eligibility (population serosurveys) and the anti-PEG barrier (PEGylated LNP only, abstains for non-PEG vehicles)." },
  ],
  caveats: [
    "No single fused immune score is asserted (collapsed_score = None on purpose): the axes measure different mechanisms on different evidence, so averaging them would manufacture certainty.",
    "Patient-specific immune MAGNITUDE (titer, realized response) is a known-unknown, never predicted; the axes are directional, not validated against a measured clinical outcome.",
  ],
};

const AXIS_COLOR = {
  pass: "var(--ok)", clear: "var(--ok)",
  abstain: "var(--warn)", flag: "var(--warn)", escalate: "var(--warn)", deferred: "var(--warn)",
  fail: "var(--bad)", refuse: "var(--bad)",
  not_evaluated: "var(--muted)", // not itself a verdict, a prior axis (biosecurity) short-circuited this one
};

// families for the multiplex-plan rows: DSB nucleases carry translocation risk; the DSB-free recombinases
// (wgenome/multiplex.py's _DSB_FREE) contribute no cut sites, so a plan built from them scores ~zero by construction.
const EDIT_FAMILIES = [
  { value: "Cas9", label: "Cas9 (DSB nuclease)" },
  { value: "Cas12a", label: "Cas12a (DSB nuclease)" },
  { value: "bridge_IS110", label: "Bridge IS110 (DSB-free)" },
  { value: "PE_integrase", label: "PE integrase (DSB-free)" },
];
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
              {v.pfam_accession && (
                <span className="text-fg-faint"> · Pfam {v.pfam_accession}, bit score {v.bit_score} (vs. gathering cutoff)</span>
              )}
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

// plain-language verdict colour (green better / grey ~reference / amber worse), matching the app's status palette.
const VERDICT_COLOR = { better: "text-ok", similar: "text-fg-dim", worse: "text-warn" };

// a compact histogram sparkline of the FLIP-AAV reference distribution with a marker at the user's score.
function CapsidDistribution({ dist, score, bucket }) {
  if (!dist || !dist.counts?.length) return null;
  const { lo, hi, counts } = dist;
  const W = 300, H = 46, n = counts.length, bw = W / n, max = Math.max(...counts, 1);
  const markX = (hi > lo ? Math.max(0, Math.min(1, (score - lo) / (hi - lo))) : 0) * W;
  const markColor = bucket === "better" ? "var(--ok)" : bucket === "worse" ? "var(--warn)" : "var(--muted)";
  return (
    <div>
      <div className="text-[11px] uppercase tracking-wide text-fg-faint">Where it falls among measured FLIP-AAV variants</div>
      <svg viewBox={`0 0 ${W} ${H}`} width="100%" style={{ maxWidth: W, height: H }} className="mt-1">
        {counts.map((cnt, i) => {
          const bh = (cnt / max) * (H - 8);
          return <rect key={i} x={i * bw + 0.5} y={H - bh} width={Math.max(0.5, bw - 1)} height={bh} rx="1" fill="var(--line)" />;
        })}
        <line x1={markX} y1={0} x2={markX} y2={H} stroke={markColor} strokeWidth="2" />
        <circle cx={markX} cy={4} r="3" fill={markColor} />
      </svg>
      <div className="flex justify-between text-[10px] text-fg-faint"><span>less fit ({lo})</span><span>more fit ({hi})</span></div>
    </div>
  );
}

// The committed FLIP-AAV Delivery-Bench: the learned capsid-fitness model vs a mutation-burden baseline on both
// splits (Spearman + bootstrap CI on the gap). Rendered verbatim from the response, never recomputed here.
function CapsidBench({ bench }) {
  const rows = [["sampled (random 80/20)", bench?.sampled], ["mut_des (mutant→designed)", bench?.mut_des]]
    .filter(([, v]) => v);
  if (!rows.length) return null;
  return (
    <div>
      <div className="text-[11px] uppercase tracking-wide text-fg-faint">Delivery-Bench · FLIP-AAV (learned vs mutation-burden baseline)</div>
      <div className="overflow-x-auto">
        <table className="mt-1 w-full text-[12px]">
          <thead><tr className="border-b border-line text-left text-[10px] uppercase tracking-wide text-fg-faint">
            <th className="py-1 pr-3">Split</th><th className="py-1 pr-3">Learned ρ</th><th className="py-1 pr-3">Baseline ρ</th>
            <th className="py-1 pr-3">Gap 95% CI</th><th className="py-1">Beats baseline</th></tr></thead>
          <tbody>
            {rows.map(([name, v]) => (
              <tr key={name} className="border-b border-line/40">
                <td className="py-1 pr-3">{name}</td>
                <td className="py-1 pr-3 tabular-nums text-brand">{v.learned_spearman}</td>
                <td className="py-1 pr-3 tabular-nums text-fg-dim">{v.baseline_spearman}</td>
                <td className="py-1 pr-3 tabular-nums">[{v.gap_ci95?.[0]}, {v.gap_ci95?.[1]}]</td>
                <td className="py-1">{v.learned_beats_baseline ? <span className="text-ok">yes</span> : <span className="text-fg-dim">no</span>}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default function DesignStudio() {
  const [design, setDesign] = useState(DEFAULT_DESIGN);
  const [mode, setMode] = useState(null);   // "verify" | "generate" | "immune", which action produced the result
  const [proof, setProof] = useState(null);
  const [verdict, setVerdict] = useState(null);
  const [gen, setGen] = useState(null);     // the /generate response
  const [imm, setImm] = useState(null);     // the /immune response (per-axis profile)
  const [immVehicle, setImmVehicle] = useState(null); // the vehicle `imm` was computed FOR (may differ from the main form)
  const [busy, setBusy] = useState(null);   // "verify" | "generate" | "immune" while running
  // multiplex plan (opt-in): 2-5 simultaneous edits, sent as design.edits so Verify can trigger the
  // multiplex.translocation_risk soft-penalty rule. Default pair matches the rule's own test fixture: two DSB
  // nucleases on different chromosomes -> a real, reproducible "flag" on first click.
  const [multiplexOn, setMultiplexOn] = useState(false);
  const [edits, setEdits] = useState([
    { chrom: "chr1", pos: 1000, family: "Cas9" },
    { chrom: "chr2", pos: 2000, family: "Cas9" },
  ]);
  function updateEdit(i, patch) { setEdits(edits.map((e, j) => (j === i ? { ...e, ...patch } : e))); }
  function addEdit() { if (edits.length < 5) setEdits([...edits, { chrom: "chr1", pos: 1000, family: "Cas9" }]); }
  function removeEdit(i) { setEdits(edits.filter((_, j) => j !== i)); }
  const [error, setError] = useState(null);
  const [openRow, setOpenRow] = useState(null);  // index of the candidate whose assembled-cassette detail is open

  // Capsid packaging fitness: learned FLIP-AAV model over an AAV VP1; AAV-only, abstains for other vectors
  const [vector, setVector] = useState("AAV");
  const [vp1, setVp1] = useState("");
  const [capFit, setCapFit] = useState(null);
  const [capBusy, setCapBusy] = useState(false);
  const [capErr, setCapErr] = useState(null);
  async function runCapsid() {
    if (!vp1.trim()) return;
    setCapBusy(true); setCapErr(null); setCapFit(null);
    try { setCapFit(await api.capsidFitness({ vp1_sequence: vp1.trim(), vector })); }
    catch (e) { setCapErr(e); setCapFit(null); } finally { setCapBusy(false); }
  }
  const [capGen, setCapGen] = useState(null);
  const [capGenBusy, setCapGenBusy] = useState(false);
  async function runCapsidGenerate() {  // distinct from the main runGenerate() below (name collision -> both fired /api/generate)
    if (!vp1.trim() || vector !== "AAV") return;
    setCapGenBusy(true); setCapErr(null); setCapGen(null);
    try { setCapGen(await api.capsidGenerate({ wt_vp1: vp1.trim() })); }
    catch (e) { setCapErr(e); setCapGen(null); } finally { setCapGenBusy(false); }
  }

  // serotype <-> tissue tropism (grounded in approved AAV therapies)
  const [serotype, setSerotype] = useState("AAV9");
  const [tropism, setTropism] = useState(null);
  const [tissue, setTissue] = useState("");
  const [tissueSero, setTissueSero] = useState(null);
  useEffect(() => {
    let live = true;
    api.serotypeTropism(serotype).then((r) => { if (live) setTropism(r); }).catch(() => { if (live) setTropism(null); });
    return () => { live = false; };
  }, [serotype]);
  function runTissue(t) {
    setTissue(t);
    if (!t) { setTissueSero(null); return; }
    api.tissueSerotypes(t).then(setTissueSero).catch(() => setTissueSero(null));
  }

  async function runVerify() {
    setBusy("verify"); setError(null);
    // a multi-edit plan must route as write_type="multiplex", that is the only write type whose rule categories
    // include `multiplex`, so the translocation_risk rule fires (an "insertion" plan never runs it).
    const d = multiplexOn && edits.length >= 2 ? { ...design, edits, write_type: "multiplex" } : design;
    try {
      const [p, v] = await Promise.all([api.verifyProof(d), api.verify(d)]);
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
  async function runImmune(d = design) {
    setBusy("immune"); setError(null);
    try { setImm(await api.immune(d)); setImmVehicle(d.delivery_vehicle ?? null); setMode("immune"); }
    catch (e) { setError(e); } finally { setBusy(null); }
  }

  const survivors = gen?.survivors || [];

  return (
    <div className="space-y-4">
      <WhatYouGet
        intro="One design surface with three actions: audit a single design, generate legal alternatives for a goal, or profile the design's delivery immunity, all under the no-fabrication invariant."
        features={[
          { name: "Verify a design", tells: "legality, calibrated confidence & biosecurity, each reported separately", output: "3 axes · pass/fail + a repairable proof" },
          { name: "Repair hint", tells: "why a design failed and how to fix it", output: "named rule + citation + repair" },
          { name: "Generate alternatives", tells: "legal, biosecurity-screened candidate designs for your goal", output: "ranked survivors + confidence band" },
          { name: "Assembled cassette", tells: "the donor construct (insulators, promoter, polyA) + codon-opt", output: "bp breakdown (expandable)" },
          { name: "Immune & delivery profile", tells: "the 5-axis delivery immune-risk vector, never collapsed", output: "per-axis 0–1 + known-unknowns" },
          { name: "Cargo-form / capacity", tells: "catches oversize cargo & mRNA-can't-carry-a-DNA-donor", output: "legal=false + citation + repair" },
          { name: "Multiplex translocation risk", tells: "can concurrent double-strand breaks in a multi-edit plan mis-join?", output: "advisory flag (2–5 edits; DSB-free writers score ~zero)" },
          { name: "Capsid packaging fitness", tells: "will an AAV capsid variant package & assemble?", output: "learned FLIP-AAV score · candidate (AAV-only)" },
          { name: "Serotype → tissue tropism", tells: "which tissue an approved AAV serotype reaches", output: "grounded prior + product + DOI (or known-unknown)" },
        ]}
        example="Verify a 3 kb AAVS1 insertion in a single AAV → all three axes pass. Bump the cargo to 8 kb → legality fails with a 'switch to dual-AAV / lentivirus' repair hint; a ricin cargo is refused before scoring."
      />
      <ScoreGuide
        intro="One design surface, three actions. VERIFY audits a single design and reports three axes separately, never collapsed, with a repairable proof. GENERATE plans real sites for your goal, sweeps the compatible vehicles, and returns the legal, screened survivors with a calibrated confidence band. PROFILE IMMUNE & DELIVERY returns the per-axis immune-risk profile for the design's vehicle, cargo and writer. Generate runs the same verifier on many candidates; Verify is the single-design check it is built on."
        items={[
          { term: "Legality", scale: "pass / fail", meaning: "A grounded rule-set check: physical feasibility (reachability, payload-vs-capacity, cargo-form ↔ vehicle, integration) plus scope-of-use compliance (heritable human germline editing is out of scope and rejected). On failure it names the rule, its citation, and a repair. It does NOT adjudicate jurisdiction-specific law or IP, dual-use hazard is the separate Biosecurity axis." },
          { term: "Confidence", scale: "0–1, may abstain", meaning: "The calibrated confidence on the soft scores; it ABSTAINS rather than guess when uncalibrated. An abstain does not block, legality and biosecurity do." },
          { term: "Biosecurity", scale: "clear / flag / escalate / refuse", meaning: "The dual-use screen over function / family / taxon signatures. A refuse short-circuits the design to a human." },
          { term: "Multiplex translocation risk", scale: "advisory flag, doesn't block", meaning: "For a 2–5 edit plan, concurrent double-strand breaks at different loci can mis-join into a translocation. A soft penalty (never fails legality), shown as an advisory flag with its risk value. DSB-free writers (bridge/PE integrase) contribute no cut sites, so a plan built from them scores ~zero by construction." },
          { term: "Survivors (Generate)", scale: "table", meaning: "Each row is a CANDIDATE the verifier judged legal and the Guardian cleared, with a calibrated confidence band, never a claim it works in vivo. An empty/refused result is by design." },
        ]}
        caveats={[
          "Verify passable = legality AND biosecurity pass (confidence may abstain). The verdict covers legality, feasibility and biosecurity, NOT efficacy.",
          "A flagged hazard is routed to a human, never auto-repaired.",
          "Biosecurity runs FIRST; a refuse short-circuits legality and confidence before they run, both then report not_evaluated (an unevaluated axis, never a fabricated fail).",
        ]} />

      <Card title="Design" subtitle="Build a proposed write, then Verify it (audit one design) or Generate alternatives (explore the goal).">
        <DesignForm design={design} onChange={setDesign} />
        {/* multiplex plan (opt-in): 2-5 simultaneous edits so Verify can trigger the multiplex translocation-risk
            screen, this rule was implemented and rule-spec-published but had no UI to reach it (tester finding). */}
        <div className="mt-3 rounded-lg border border-line bg-ink-900 p-3">
          <label className="flex items-center gap-2 text-sm text-fg-dim">
            <input type="checkbox" checked={multiplexOn} onChange={(e) => setMultiplexOn(e.target.checked)} />
            Plan multiple simultaneous edits <span className="text-fg-faint">(2–5, enables the multiplex translocation-risk screen)</span>
          </label>
          {multiplexOn && (
            <>
              <div className="mt-2 space-y-2">
                {edits.map((e, i) => {
                  const chromBad = (e.chrom || "").trim() && !CHROMS.includes(e.chrom.trim());
                  return (
                  <div key={i}>
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="w-5 text-[11px] text-fg-faint">#{i + 1}</span>
                      <input className="input w-24 font-mono text-xs" placeholder="chrom" value={e.chrom}
                             style={chromBad ? { borderColor: "var(--warn)" } : undefined}
                             onChange={(ev) => updateEdit(i, { chrom: ev.target.value })} />
                      {/* genomic position is a non-negative coordinate; clamp to >= 0 rather than accept a negative */}
                      <input type="number" min={0} className="input w-32 font-mono text-xs" placeholder="position (bp)" value={e.pos}
                             onChange={(ev) => updateEdit(i, { pos: clampInt(ev.target.value, 0, 300000000, 0).value })} />
                      <div className="w-52"><Select value={e.family} onChange={(v) => updateEdit(i, { family: v })} options={EDIT_FAMILIES} /></div>
                      {edits.length > 2 && (
                        <button onClick={() => removeEdit(i)} className="text-xs text-fg-faint hover:text-warn">remove</button>
                      )}
                    </div>
                    {chromBad && (
                      <p className="mt-0.5 pl-7 text-[11px]" style={{ color: "var(--warn)" }}>
                        ⚠ &quot;{e.chrom}&quot; is not a valid chromosome (chr1–chr22, chrX, chrY, chrM).
                      </p>
                    )}
                  </div>
                  );
                })}
              </div>
              <div className="mt-2 flex flex-wrap items-center gap-3">
                {edits.length < 5 && (
                  <button onClick={addEdit} className="rounded border border-line px-2 py-1 text-xs text-fg-dim hover:border-brand/40 hover:text-fg">+ add edit</button>
                )}
                <span className="text-[11px] text-fg-faint">Concurrent double-strand breaks at different loci can mis-join into a translocation; DSB-free writers (bridge/PE integrase) carry ~zero risk by construction. Fires as an advisory flag on Verify, it does not block legality.</span>
              </div>
            </>
          )}
        </div>
        <div className="mt-4 flex flex-wrap gap-3">
          <Button onClick={runVerify} disabled={!!busy}>{busy === "verify" ? "Verifying…" : "Verify this design"}</Button>
          <Button onClick={runGenerate} disabled={!!busy} variant="secondary">{busy === "generate" ? "Generating…" : "Generate alternatives"}</Button>
          <Button onClick={() => runImmune()} disabled={!!busy} variant="secondary">{busy === "immune" ? "Profiling…" : "Profile immune & delivery"}</Button>
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
              {(() => {
                const flags = (verdict?.scope_flags || []).filter((f) => String(f.kind || "").startsWith("chromosome_"));
                if (!flags.length) return null;
                return (
                  <div className="rounded border border-border p-3">
                    <strong className="text-sm">Site &amp; chromosome notes</strong>
                    <ul className="mt-2 text-sm text-fg-dim space-y-1">
                      {flags.map((f, i) => (
                        <li key={i} style={f.kind === "chromosome_invalid" || f.kind === "chromosome_mismatch" ? { color: "var(--warn)" } : undefined}>
                          <code>{f.kind.replace("chromosome_", "chrom: ")}</code> {f.reason}
                        </li>
                      ))}
                    </ul>
                  </div>
                );
              })()}
              {/* soft-penalty rules (e.g. multiplex translocation risk) never block legality, but were never
                  rendered anywhere, verdict.soft_flags was already returned, just not surfaced (tester finding) */}
              {(verdict?.soft_flags || []).length > 0 && (
                <div className="rounded border border-warn/25 bg-warn/5 p-3">
                  <strong className="text-sm text-warn">Advisory flags</strong>
                  <span className="ml-1.5 text-[11px] text-fg-faint">(soft penalties, do not block legality)</span>
                  <ul className="mt-2 text-sm text-fg-dim space-y-1">
                    {verdict.soft_flags.map((f, i) => (
                      <li key={i}><code>{f.rule_id}</code>: {f.reason}
                        {f.value != null && <span className="text-fg-faint"> (value {typeof f.value === "number" ? f.value.toFixed(3) : String(f.value)})</span>}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
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
              <p className="mt-3 text-[11px] text-fg-faint">No protocol is emitted and no candidate is scored, a biosecurity refusal by design.</p>
            </div>
          ) : survivors.length === 0 ? (
            <p className="text-sm text-fg-dim">No candidates survived. Either every swept variant was illegal/hazardous, or the engine found no writable plan for this gene + cell type (try a safe-harbour locus such as AAVS1, or a cell type with a measured atlas: K562 / HepG2 / HSPC). An empty set is by design.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-line text-left text-[11px] uppercase tracking-wide text-fg-faint">
                    <th className="py-2 pr-3">Vehicle</th><th className="py-2 pr-3">Writer</th><th className="py-2 pr-3">Site</th><th className="py-2 pr-3">Cargo bp</th>
                    <th className="py-2 pr-3">Legal</th><th className="py-2 pr-3">Safety</th><th className="py-2 pr-3 w-48">Confidence</th><th className="py-2 pr-3">Flags</th><th className="py-2">Cassette</th>
                  </tr>
                </thead>
                <tbody>
                  {survivors.map((s, i) => (
                    <React.Fragment key={i}>
                    <tr className="border-b border-line/50 align-middle">
                      <td className="py-2 pr-3 font-medium">{String(s.delivery_vehicle).replace(/_/g, " ")}</td>
                      <td className="py-2 pr-3 text-fg-dim">{s.writer_family ? String(s.writer_family).replace(/_/g, " ") : "-"}</td>
                      <td className="py-2 pr-3 font-mono text-[11px] text-fg-dim">{s.site ? `${s.site.chrom}:bin${s.site.bin}` : "-"}</td>
                      <td className="py-2 pr-3 tabular-nums text-fg-dim">{s.cargo_bp}</td>
                      <td className="py-2 pr-3">{s.legal ? <span className="text-ok">legal</span> : <span className="text-bad">no</span>}</td>
                      <td className="py-2 pr-3"><SafetyBadge decision={s.safety_decision} compact /></td>
                      <td className="py-2 pr-3">
                        {s.confidence != null
                          ? <ConfidenceBand lo={s.interval?.[0]} hi={s.interval?.[1]} point={s.confidence} status="grounded" />
                          : <span className="text-fg-faint text-xs" title="This cell type has no measured writability atlas (only K562 / HepG2 / HSPC do), so the planner cannot compute calibrated scores. Legality and biosecurity still ran.">abstained · no measured atlas for this cell type</span>}
                      </td>
                      <td className="py-2 pr-3">{s.scope_flags?.length ? <Pill color="var(--warn)">{s.scope_flags.length} scope</Pill> : <span className="text-fg-faint text-xs">none</span>}</td>
                      <td className="py-2">{s.cargo?.elements
                        ? <button type="button" onClick={() => setOpenRow(openRow === i ? null : i)} className="text-[11px] text-brand hover:underline">{openRow === i ? "hide" : "view"}</button>
                        : <span className="text-fg-faint text-xs">-</span>}</td>
                    </tr>
                    {openRow === i && s.cargo?.elements && (
                      <tr className="border-b border-line/50 bg-ink-900/50">
                        <td colSpan={9} className="px-3 py-2">
                          <div className="text-[11px] text-fg-dim">
                            <span className="font-semibold text-fg">Assembled cassette</span>, payload {s.cargo.payload_bp} bp +{" "}
                            {Object.entries(s.cargo.elements).map(([k, v]) => `${k.replace(/_/g, " ")} ${v} bp`).join(" · ")}{" "}
                            = <b className="text-fg">{s.cargo.assembled_bp} bp assembled</b>
                            {s.cargo.codon_optimised ? <span className="text-ok"> · codon-optimised</span> : null}
                            {s.cargo.cargo_capacity_bp != null && <span className="text-fg-faint"> · writer capacity {s.cargo.cargo_capacity_bp} bp · {s.cargo.size_ok ? <span className="text-ok">fits</span> : <span className="text-bad">over capacity</span>}</span>}
                          </div>
                        </td>
                      </tr>
                    )}
                    </React.Fragment>
                  ))}
                </tbody>
              </table>
              <p className="mt-3 text-[11px] text-fg-faint">Each row is a candidate the verifier judged legal and the Guardian cleared, with a calibrated confidence band; the <b>Cassette</b> column expands the assembled donor construct (insulators, promoter, polyA + codon-opt). None is a claim that it will work in vivo.</p>
              <p className="mt-1 text-[11px] text-fg-faint">This sweep covers <b>delivery vehicles × writers</b> for your goal. To score whether a specific AAV capsid variant will package, use the <b>Capsid packaging fitness</b> card below (learned FLIP-AAV model); <i>generating</i> novel capsid variants is a separate, model-gated capability not proposed here.</p>
            </div>
          )}
        </Card>
      )}

      {/* IMMUNE result: the per-axis immune-risk profile (absorbs the former Delivery & Immunity page) */}
      {mode === "immune" && !error && (
        <>
          <ScoreGuide intro={IMMUNE_GUIDE.intro} items={IMMUNE_GUIDE.items} caveats={IMMUNE_GUIDE.caveats} />
          <Card title="Immune-risk profile" subtitle="Switch the vehicle to watch the axes move, the engine recomputes each. Five axes, never collapsed.">
            {/* highlight the vehicle the profile was COMPUTED for (immVehicle), NOT the main form's current selection
, otherwise the main dropdown moves the highlight while the numbers below stay stale. */}
            <div className="mb-3 flex flex-wrap gap-1.5">
              {VEHICLES.map((v) => (
                <button key={v} onClick={() => { const d = { ...design, delivery_vehicle: v }; setDesign(d); runImmune(d); }}
                  className={`rounded-lg border px-2.5 py-1 text-xs ${immVehicle === v ? "border-brand/50 bg-brand/15 text-brand" : "border-line bg-ink-900 text-fg-dim hover:text-fg"}`}>
                  {v.replace(/_/g, " ")}
                </button>
              ))}
            </div>
            {/* the main-form Delivery vehicle can change without re-profiling → say so plainly, never show stale numbers as current */}
            {immVehicle && design.delivery_vehicle !== immVehicle && (
              <p className="mb-3 rounded-lg border border-warn/25 bg-warn/5 px-3 py-2 text-[11px] leading-relaxed text-amber-300/80">
                These axes are for <b>{String(immVehicle).replace(/_/g, " ")}</b>, the vehicle they were computed for.
                The form&apos;s Delivery vehicle now selects <b>{String(design.delivery_vehicle).replace(/_/g, " ")}</b>;
                click its chip above (or press <b>Profile immune &amp; delivery</b>) to recompute for it.
              </p>
            )}
            <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_300px]">
              <div>
                {busy === "immune" ? <Spinner /> : !imm ? null : <ImmuneProfileCard profile={imm} />}
              </div>
              <div>
                {imm && <ScopeLedger knownUnknowns={imm.known_unknowns} />}
                {imm?.note && <p className="mt-3 text-[11px] text-fg-faint">{imm.note}</p>}
              </div>
            </div>
          </Card>
        </>
      )}

      {!mode && !error && (
        <Card title="Result"><p className="text-sm text-fg-faint">Verify a design for its 3-axis proof, Generate alternatives to sweep the goal for legal screened candidates, or Profile immune &amp; delivery for the per-axis immune-risk profile.</p></Card>
      )}

      {/* Serotype -> tissue tropism: grounded priors from FDA/EMA-approved AAV gene therapies */}
      <Card title="Serotype → tissue tropism"
            subtitle="Which tissue an approved AAV serotype reaches, grounded priors from FDA/EMA-approved gene therapies, each with the product + citation. A novel / engineered capsid returns a known-unknown, never a fabricated tissue.">
        <div className="grid gap-4 lg:grid-cols-2">
          <div>
            <label className="mb-1 block text-[11px] uppercase tracking-wide text-fg-faint">By serotype → tissue</label>
            <select className="input" value={serotype} onChange={(e) => setSerotype(e.target.value)}>
              <option value="AAV9">AAV9 (BBB-crossing)</option>
              <option value="AAVrh74">AAVrh74</option>
              <option value="AAV5">AAV5</option>
              <option value="AAVRh74var">AAVRh74var</option>
              <option value="AAV2">AAV2</option>
              <option value="AAV_novel_xyz">Novel / engineered capsid</option>
            </select>
            {tropism && (
              <div className="mt-3 rounded-lg border border-line bg-ink-900 p-3 text-sm">
                {tropism.tissue ? (
                  <div className="space-y-2">
                    <div className="flex flex-wrap items-center gap-2">
                      {(tropism.tissue || []).map((t) => <Pill key={t} color="var(--brand)">{String(t).replace(/_/g, " ")}</Pill>)}
                      <Pill color="var(--ok)">{tropism.confidence}</Pill>
                    </div>
                    <p className="text-[12px] text-fg-dim"><b className="text-fg">Route:</b> {tropism.route}</p>
                    <p className="text-[12px] text-fg-dim"><b className="text-fg">Evidence:</b> {tropism.evidence}{tropism.indication ? `, ${tropism.indication}` : ""} ({tropism.approval})</p>
                    {tropism.doi && <a href={`https://doi.org/${tropism.doi}`} target="_blank" rel="noreferrer" className="text-[11px] text-brand hover:underline">doi:{tropism.doi}</a>}
                  </div>
                ) : (
                  <p className="text-[12px] leading-relaxed text-amber-200"><b>Known-unknown.</b> {tropism.note}{" "}
                    <span className="text-fg-faint">Tissue for an untested capsid can’t be predicted, but you can screen its packaging fitness and generate fitness-gated variants in the Capsid packaging fitness card below.</span></p>
                )}
              </div>
            )}
          </div>
          <div>
            <label className="mb-1 block text-[11px] uppercase tracking-wide text-fg-faint">By target tissue → serotype</label>
            <select className="input" value={tissue} onChange={(e) => runTissue(e.target.value)}>
              <option value="">Choose a tissue…</option>
              <option value="liver">Liver</option>
              <option value="CNS">CNS</option>
              <option value="muscle">Muscle</option>
              <option value="retina">Retina</option>
            </select>
            {tissueSero && (
              <div className="mt-3 rounded-lg border border-line bg-ink-900 p-3 text-sm">
                {(tissueSero.grounded_serotypes || []).length ? (
                  <ul className="space-y-2">
                    {tissueSero.grounded_serotypes.map((s, i) => (
                      <li key={i} className="text-[12px] text-fg-dim">
                        <b className="text-fg">{s.serotype}</b> → {(s.tissue || []).map((t) => String(t).replace(/_/g, " ")).join(", ")}
                        <span className="text-fg-faint"> · {s.evidence}</span>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-[12px] leading-relaxed text-amber-200">{tissueSero.note}</p>
                )}
              </div>
            )}
          </div>
        </div>
        <p className="mt-3 text-[11px] leading-relaxed text-fg-faint">Population-level priors from approved-therapy precedent, strongest for the approved <b>route</b> (e.g. AAV2 retina/CNS is LOCAL injection, not systemic; AAVrh74 muscle vs AAVRh74var liver are different capsids). A capsid with no approved precedent → in-vivo human tropism is a known-unknown, never fabricated.</p>
      </Card>

      {/* Capsid packaging fitness: learned FLIP-AAV model, does a given capsid VP1 package/assemble? */}
      <Card title="Capsid packaging fitness"
            subtitle="Will a capsid variant package and assemble? The learned FLIP-AAV model scores an AAV VP1's packaging fitness, a candidate for the measured packaging axis, not an in-vivo tropism claim. AAV-only: other vectors (LV, adenovirus, HSV) have no learned packaging-fitness model and abstain.">
        <div className="mb-4 rounded-lg border border-line bg-ink-900/60 p-3 text-[12px] leading-relaxed text-fg-dim">
          <p className="mb-1.5 font-semibold text-fg">How it works</p>
          <ul className="space-y-1.5">
            <li><b className="text-fg">What it predicts, </b> whether an AAV capsid variant will <b>package &amp; assemble</b> the genome: one score (log-enrichment; <b>higher = more fit</b>). It does <b>not</b> predict tropism, transduction, or in-vivo behaviour.</li>
            <li><b className="text-fg">How, </b> a gradient-boosting model trained on the <b>FLIP-AAV</b> benchmark reads VP1 <b>residues 555–595</b> (the mutagenised surface loop) and scores that window. It beats a mutation-burden baseline on both splits (ρ 0.92 &amp; 0.81; CI excludes 0), see the bench below.</li>
            <li><b className="text-fg">What to give it, </b> a <b>full-length AAV VP1</b> capsid protein (≥ 595 aa, AAV2 numbering). It reads <b>only residues 555–595</b>, so changes elsewhere are invisible; novelty <i>within</i> that loop is supported (validated on the mutant→designed split). Too-short or non-protein inputs are <b>refused, not guessed</b>.</li>
            <li><b className="text-fg">How to read it, </b> the result leads with a plain-language verdict + the <b>percentile</b> among measured FLIP-AAV variants (so "top 10%", not "−4.6"), the raw log-enrichment is shown small. It is <b>relative</b>, not an absolute pass/fail; every value is a labelled <b>candidate</b>.</li>
            <li><b className="text-fg">Generate, </b> "Generate variants" proposes new VP1 555–595 variants of your sequence and keeps only those with <b>fitness ≥ WT</b> (the generator proposes, the model disposes). Packaging fitness only, assembly, tropism and <b>immunogenicity are not scored here</b> (deferred to the immune profile); run verify + biosecurity before any synthesis.</li>
          </ul>
        </div>
        <div className="grid gap-3 sm:grid-cols-[200px_minmax(0,1fr)]">
          <div>
            <label className="mb-1 block text-[11px] uppercase tracking-wide text-fg-faint">Vector</label>
            <select className="input" value={vector} onChange={(e) => { setVector(e.target.value); setCapFit(null); }}>
              <option value="AAV">AAV (learned model)</option>
              <option value="Lentivirus">Lentivirus (LV)</option>
              <option value="Adenovirus">Adenovirus</option>
              <option value="HSV">HSV</option>
            </select>
          </div>
          <div>
            <label className="mb-1 block text-[11px] uppercase tracking-wide text-fg-faint">
              {vector === "AAV" ? "Capsid VP1 sequence (the model reads residues 555–595)" : `${vector} capsid / envelope sequence`}
            </label>
            <textarea className="input h-20 font-mono text-[11px]" placeholder="Paste the capsid protein sequence (amino acids)…"
                      value={vp1} onChange={(e) => setVp1(e.target.value)} />
          </div>
        </div>
        <div className="mt-3 flex flex-wrap items-center gap-3">
          <Button onClick={runCapsid} loading={capBusy} disabled={!vp1.trim()}>{capBusy ? "Scoring…" : "Score packaging fitness"}</Button>
          {vector === "AAV" && <Button onClick={runCapsidGenerate} loading={capGenBusy} disabled={!vp1.trim()} variant="secondary">{capGenBusy ? "Generating…" : "Generate variants (fitness ≥ WT)"}</Button>}
          {vector !== "AAV" && <span className="text-[11px] text-warn">No learned packaging-fitness model for {vector}, the engine will say so, not guess.</span>}
        </div>
        {capErr && <div className="mt-3"><ErrorNote error={capErr} /></div>}
        {capFit && (
          <div className="mt-4">
            {capFit.available ? (
              <div className="space-y-3">
                <div className="flex flex-wrap items-center gap-3">
                  <span className={`text-lg font-semibold ${VERDICT_COLOR[capFit.verdict_bucket] || "text-fg"}`}>{capFit.verdict}</span>
                  <Pill color="var(--warn)">candidate</Pill>
                </div>
                <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1 text-[12px] text-fg-faint">
                  {capFit.percentile != null && <span className="tabular-nums">better than <b className={VERDICT_COLOR[capFit.verdict_bucket] || "text-fg"}>{capFit.percentile}%</b> of measured FLIP-AAV variants</span>}
                  <span>raw score {capFit.predicted_fitness} · log-enrichment (higher = fitter)</span>
                </div>
                {capFit.distribution && <CapsidDistribution dist={capFit.distribution} score={capFit.predicted_fitness} bucket={capFit.verdict_bucket} />}
                {capFit.input_warning && (
                  <p className="rounded border border-warn/30 bg-warn/5 px-2 py-1 text-[11px] leading-relaxed text-amber-200">⚠ {capFit.input_warning}</p>
                )}
                <p className="text-[11px] leading-relaxed text-fg-faint">{capFit.status}</p>
                {capFit.bench && <CapsidBench bench={capFit.bench} />}
              </div>
            ) : (
              <div className="rounded-lg border border-warn/30 bg-warn/5 p-3">
                <p className="text-[12px] leading-relaxed text-amber-200"><b>{capFit.input_issue ? "Can’t score this input." : "Abstained (no fabrication)."}</b> {capFit.note}</p>
                {capFit.bench && <div className="mt-3"><CapsidBench bench={capFit.bench} /></div>}
              </div>
            )}
          </div>
        )}
        {capGen && (
          <div className="mt-4">
            {capGen.available ? (
              <div className="space-y-2">
                <p className="text-[12px] text-fg-dim">
                  <b className="text-fg">{capGen.n_survivors}</b> of {capGen.n_proposed} proposed variants pass the
                  fitness ≥ WT gate (WT fitness <b>{capGen.wt_predicted_fitness}</b>, threshold {capGen.fitness_threshold}).
                  Each is a <Pill color="var(--warn)">candidate</Pill>, the generator proposes, the fitness model disposes.
                </p>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead><tr className="border-b border-line text-left text-[11px] uppercase tracking-wide text-fg-faint">
                      <th className="py-1.5 pr-3">#</th><th className="py-1.5 pr-3">VP1 555–595 variant window</th>
                      <th className="py-1.5 pr-3">Mutations</th><th className="py-1.5 pr-3">Predicted fitness</th><th className="py-1.5">Δ vs WT</th></tr></thead>
                    <tbody>
                      {capGen.candidates.map((cand, i) => (
                        <tr key={i} className="border-b border-line/40">
                          <td className="py-1.5 pr-3 tabular-nums text-fg-faint">{i + 1}</td>
                          <td className="py-1.5 pr-3 break-all font-mono text-[10px] text-fg-dim">{cand.vp1_window}</td>
                          <td className="py-1.5 pr-3 tabular-nums">{cand.n_mut_in_region}</td>
                          <td className="py-1.5 pr-3 tabular-nums text-fg-dim">{cand.predicted_fitness}</td>
                          <td className="py-1.5 tabular-nums text-ok">+{(cand.predicted_fitness - capGen.wt_predicted_fitness).toFixed(3)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                <p className="text-[11px] leading-relaxed text-fg-faint">{capGen.honesty}</p>
              </div>
            ) : (
              <div className="rounded-lg border border-warn/30 bg-warn/5 p-3">
                <p className="text-[12px] leading-relaxed text-amber-200"><b>Abstained (no fabrication).</b> {capGen.note}</p>
              </div>
            )}
          </div>
        )}
      </Card>
    </div>
  );
}
