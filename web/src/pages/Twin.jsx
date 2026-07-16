// Digital Twin, a calibrated, OOD-gated, phenotype-bounded outcome prediction. The scope discipline here is structural:
// the band is a heuristic interval that WIDENS under OOD (not a trained conformal interval, no public
// perturbation-outcome calibration set), and the structure→phenotype boundary is never crossed.
import React, { useState, useEffect } from "react";
import WhatYouGet from "../components/WhatYouGet.jsx";
import { api } from "../api.js";
import { Card, Button, Spinner, ErrorNote, Pill, Stat, Field, Select } from "../components/ui.jsx";
import DesignForm, { DEFAULT_DESIGN, CELLS } from "../components/DesignForm.jsx";
import ConfidenceBand from "../components/ConfidenceBand.jsx";
import ImmuneProfileCard from "../components/ImmuneProfileCard.jsx";
import ScoreGuide from "../components/ScoreGuide.jsx";
import { num } from "../lib/format.js";

// the human-K562 head (Leemans 2019) reads these 5 histone marks; a chromatin context enables the learned position-effect head
const MARKS = ["H3K27ac", "H3K4me1", "H3K9me3", "H3K27me3", "H3K36me3"];
const DEMO_K562_MARKS = { H3K27ac: 1.0, H3K4me1: 0.5, H3K9me3: 0.0, H3K27me3: 0.0, H3K36me3: 0.5 };

// which learned head served, from the position_effect scope flags
function servedHead(pe) {
  const f = (pe.scope_flags || []).find((s) => /human_K562/i.test(s));
  if (f) return { name: "Human K562 head", dataset: "Leemans 2019", human: true };
  return { name: "mESC head", dataset: "TRIP mESC", human: false };
}

function StageHCard({ pe }) {
  const head = servedHead(pe);
  const validated = pe.outcome_validated;
  const iv = pe.interval_log2;
  return (
    <Card title="position-effect model" subtitle="Which learned head served this design, and at what validation resolution.">
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
        <Stat label="Served head" value={head.name} />
        <Stat label="Feature resolution" value={pe.served_feature_resolution} />
        <Stat label="Outcome-validated" value={validated ? "yes" : "no"} color={validated ? "var(--ok)" : "var(--warn)"} />
        {/* v7.3.14 surfaced this; v7.3.16 tempers the framing (tester found it usually reads ×3). THIS is the
            model's own OOD signal (Mahalanobis distance over the 5 marks), distinct from the top-level "OOD"
            stat (a different oracle's cell-type/perturbation scope card). It DOES vary (near ×1 for near-zero
            input, ×2.4–×2.8 mid-range, ×3 cap for extreme), but the served head was trained on EXACT-SITE
            NORMALIZED features, so typical coarse 1kb-atlas 0–1 marks sit outside that distribution and it
            usually reads HIGH (near the cap). That high value is the widen CORRECTLY flagging OOD, the same
            root cause as outcome_validated:false at this resolution, not a stuck number. */}
        {pe.ood_widen != null && (
          <Stat label="OOD widen (this head)" value={`×${num(pe.ood_widen)}`}
                color={pe.ood_widen >= 3 ? "var(--bad)" : pe.ood_widen > 1.3 ? "var(--warn)" : "var(--ok)"} />
        )}
      </div>
      <div className="mt-3 grid grid-cols-3 gap-2 text-sm">
        <div><div className="text-[11px] uppercase tracking-wide text-fg-faint">Learned log2 expr</div><div className="tabular-nums text-brand">{num(pe.predicted_log2_expression)}</div></div>
        <div><div className="text-[11px] uppercase tracking-wide text-fg-faint">Interval (log2)</div><div className="tabular-nums">{iv ? `[${num(iv[0])}, ${num(iv[1])}]` : "-"}</div></div>
        <div><div className="text-[11px] uppercase tracking-wide text-fg-faint">p(silenced)</div><div className="tabular-nums">{num(pe.p_silenced)}</div></div>
      </div>
      {head.human && !validated && (
        <p className="mt-3 rounded-lg border border-warn/25 bg-warn/5 px-3 py-2 text-[11px] leading-relaxed text-amber-300/80">
          <strong>Not outcome-validated at this resolution.</strong> The human K562 head&apos;s held-out result (ρ≈0.57;
          Leemans 2019, chromosome-blocked, +0.065 over a learned-heterochromatin baseline, CI[0.026,0.103]) holds at{" "}
          <b>exact-site</b> per-locus chromatin features. The app currently serves coarse 1&nbsp;kb atlas features, so the
          flag reports <code>outcome_validated: false</code> (realized ρ≈0.16). Serve-time exact-site extraction
          (v7.4) reaches the validated regime.{" "}
          <b>This is also why the OOD-widen factor above usually reads near its ×3 ceiling:</b> the head was trained on
          normalized exact-site features, so typical 0–1 histone inputs at this coarse resolution sit outside that
          distribution and the widen correctly flags them as out-of-distribution (near-zero inputs read ~×1; it is
          computed from your mark vector, not fixed).
        </p>
      )}
      {head.human && validated && (
        <p className="mt-3 rounded-lg border border-emerald-500/25 bg-emerald-500/5 px-3 py-2 text-[11px] leading-relaxed text-emerald-300/80">
          <strong>Outcome-validated regime.</strong> Served at exact-site feature resolution, the human K562 head&apos;s
          held-out ρ≈0.57 (Leemans 2019; chromosome-blocked; +0.065 over a learned-heterochromatin baseline, CI[0.026,0.103]).
        </p>
      )}
      <p className="mt-2 text-[11px] text-fg-faint">{pe.provenance}</p>
    </Card>
  );
}

export default function Twin() {
  const [design, setDesign] = useState(DEFAULT_DESIGN);
  const [cellState, setCellState] = useState("k562");
  const [useChromatin, setUseChromatin] = useState(false);
  const [marks, setMarks] = useState(DEMO_K562_MARKS);
  const [promoters, setPromoters] = useState([]); // the selectable promoter palette (a LIVE lever on expression)
  const [res, setRes] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => { api.promoters().then((r) => setPromoters(r.promoters || [])).catch(() => {}); }, []);

  async function run() {
    setBusy(true); setError(null);
    // supplying a chromatin context (the head's 5 marks) enables the learned position-effect head; declared coarse (1 kb
    // atlas) resolution, so the resolution-aware flag reports outcome_validated:false until v7.4 exact-site.
    // marks are held as raw strings while editing (so a leading "-" isn't mangled mid-type); coerce to numbers here.
    const numericMarks = Object.fromEntries(MARKS.map((m) => [m, parseFloat(marks[m]) || 0]));
    const d = useChromatin
      ? { ...design, chromatin_features: numericMarks, chromatin_features_resolution: "1kb_atlas" }
      : design;
    try { setRes(await api.predict({ design: d, cell_state: cellState })); } catch (e) { setError(e); setRes(null); } finally { setBusy(false); }
  }

  const po = res?.predicted_outcome;
  const iv = res?.interval;
  const point = po?.relative_expression;
  const status = res?.extrapolating ? "extrapolating" : "grounded";
  const selPromoter = promoters.find((p) => p.name === design.promoter);
  // the 5 marks are documented normalized signal in [0,1]; flag any out-of-range value (fed to the model as-is).
  // marks may be raw strings mid-edit, so parse before comparing (a partial "-"/"" parses to NaN and is skipped).
  const marksOutOfRange = useChromatin
    ? MARKS.filter((m) => { const v = parseFloat(marks[m]); return Number.isFinite(v) && (v < 0 || v > 1); })
    : [];

  return (
    <div className="space-y-4">
      <WhatYouGet
        intro="A calibrated, out-of-distribution-gated prediction of how a design will express once integrated, bounded by what is actually knowable, never a clinical or phenotypic guarantee."
        features={[
          { name: "Outcome prediction", tells: "the relative molecular outcome (expression / durability) for a design", output: "point + uncertainty band" },
          { name: "Promoter palette", tells: "how the chosen promoter drives the mechanistic estimate (31 constitutive + tissue-specific, cited)", output: "a live lever on relative expression" },
          { name: "Cargo-capacity feasibility", tells: "whether the cargo fits the vehicle (relative expression is per-copy, cargo-size-independent)", output: "buildable / not-buildable note" },
          { name: "OOD gating", tells: "how far the design is from what the model has seen, TWO separate checks: the response oracle's cell-type/perturbation scope card, and the position-effect chromatin model's own Mahalanobis-distance widen factor", output: "OOD (response model) yes/no + the position-effect card's OOD widen ×1–×3" },
          { name: "Learned position-effect head", tells: "which position-effect head served (human K562 / mESC) and its validation resolution", output: "served head + outcome_validated flag" },
          { name: "Known-unknowns", tells: "quantities it will never predict (in-vivo titer, phenotype, clinical durability)", output: "returned as known-unknowns, not guessed" },
        ]}
        example="A cassette at AAVS1 in K562 → a calibrated expression band; supply a K562 chromatin context and the human K562 head (Leemans 2019) serves, flagged not-outcome-validated at the app's coarse 1 kb resolution."
      />
      <ScoreGuide
        intro="The twin predicts a RELATIVE molecular outcome with an uncertainty band. It is a bounded estimate for decision-support, never a clinical or phenotypic guarantee."
        items={[
          { term: "Relative expression", scale: "relative, dimensionless", meaning: "The mechanistic modeled expression of the insert (promoter strength × copy number × accessibility × pre-existing-NAb), higher = stronger, a relative quantity, not an absolute titer. It reacts to the promoter and delivery vehicle; it is cell-type-agnostic (the cell-type position effect is the learned position-effect head), and per-copy (independent of cargo size)." },
          { term: "Outcome band", scale: "interval, WIDENS on OOD", meaning: "A heuristic interval that widens when the query leaves the model's validity envelope. interval_kind states exactly what kind of interval it is (it is not a trained conformal interval, no public perturbation-outcome calibration set exists)." },
          { term: "Learned position-effect head", scale: "served head + resolution", meaning: "When a chromatin context is supplied, a learned position-effect head serves. A human K562 design uses the human K562 head (Leemans 2019); its validated ρ≈0.57 is earned only at exact-site feature resolution, so at the app's coarse 1 kb resolution outcome_validated is false." },
          { term: "OOD (response model)", scale: "yes / no", meaning: "Checks the virtual-cell RESPONSE oracle's own scope card (documented in-distribution cell types + perturbation kinds). Every cell type this page's dropdown offers is on that list, so this reads \"no\" through this UI by construction, a different signal from the position-effect card's own OOD check below." },
          { term: "OOD widen (position-effect head)", scale: "×1 – ×3", meaning: "The chromatin position-effect model's own out-of-distribution multiplier (Mahalanobis distance over the 5 supplied marks vs. its training distribution; near-zero input ≈ ×1, mid-range ≈ ×2.4–×2.8, cap ×3). It is computed from your mark vector, not fixed, but note the head was trained on normalized EXACT-SITE features, so typical 0–1 histone inputs at the app's coarse 1 kb resolution sit outside that distribution and usually read near the ×3 cap. That is the widen correctly flagging OOD, the same root cause as outcome_validated:false, not a stuck value." },
        ]}
        caveats={[
          "Bounded by the structure→phenotype boundary: in-vivo titer, phenotype and clinical durability are known-unknowns, never predicted.",
          "The learned position-effect head is served at coarse 1 kb feature resolution; the human head's validated ρ≈0.57 regime needs exact-site per-locus features (serve-time extraction, v7.4).",
        ]} />
      <div className="grid gap-4 lg:grid-cols-2">
      <Card title="Design & cell state" subtitle="The twin predicts a relative outcome conditioned on the cell state.">
        <DesignForm design={design} onChange={setDesign} />
        <div className="mt-3 grid gap-3 sm:grid-cols-2">
          <Field label="Cell state"><Select value={cellState} onChange={setCellState} options={CELLS} /></Field>
          {/* the promoter is a LIVE lever on the mechanistic estimate (was computed but not selectable, tester finding) */}
          <Field label="Promoter (drives relative expression)">
            <Select value={design.promoter || ""} onChange={(v) => setDesign({ ...design, promoter: v || undefined })}
              options={[{ value: "", label: "default (0.5)" },
                        ...promoters.map((p) => ({ value: p.name, label: `${p.name} · ${p.strength} · ${p.group === "tissue_specific" ? p.context : "constitutive"}` }))]} />
            {/* v7.3.16 (tester finding): a tissue-specific promoter (e.g. TBG=liver) picked for a mismatched cell
                state still returns a full mechanistic score, because that estimate is cell-type-agnostic. Warn so a
                user is not misled into reading a maximally-optimistic number for a biologically inappropriate pick. */}
            {selPromoter?.group === "tissue_specific" && (
              <p className="mt-1 text-[12px]" style={{ color: "var(--warn)" }}>
                ⚠ {selPromoter.name} is a <b>{selPromoter.context}</b>-specific promoter. The mechanistic estimate is
                cell-type-agnostic, it applies the same strength whether or not <b>{selPromoter.context}</b> matches
                your cell state (<b>{cellState}</b>), so confirm this promoter is actually active in your target cells.
              </p>
            )}
          </Field>
        </div>
        {/* optional chromatin context, supplying the head's 5 marks enables the learned position-effect head */}
        <div className="mt-3 rounded-lg border border-line bg-ink-900 p-3">
          <label className="flex items-center gap-2 text-sm text-fg-dim">
            <input type="checkbox" checked={useChromatin} onChange={(e) => setUseChromatin(e.target.checked)} />
            Supply a chromatin context <span className="text-fg-faint">(enables the learned position-effect head)</span>
          </label>
          {useChromatin && (
            <>
              <div className="mt-2 grid grid-cols-2 gap-2 sm:grid-cols-3">
                {MARKS.map((m) => (
                  <div key={m}>
                    <div className="mb-0.5 text-[10px] uppercase tracking-wide text-fg-faint">{m}</div>
                    {/* stored as a raw string while editing so a leading "-" is not stripped mid-type (tester
                        finding: "-5" became "05"); no native min/max so an out-of-range value can be entered and
                        FLAGGED rather than blocked. Coerced to a number at predict time (run()). */}
                    <input type="number" step="0.1"
                           className="input font-mono text-xs"
                           style={(() => { const v = parseFloat(marks[m]); return Number.isFinite(v) && (v < 0 || v > 1) ? { borderColor: "var(--warn)" } : undefined; })()}
                           value={marks[m]}
                           onChange={(e) => setMarks({ ...marks, [m]: e.target.value })} />
                  </div>
                ))}
              </div>
              {/* v7.3.16 (tester finding): the marks are documented normalized signal in [0,1] but the field
                  accepted e.g. -5 with no warning and fed it straight to the model. Flag out-of-range values
                  (kept, not clamped, so the OOD-widen signal still reflects them). */}
              {marksOutOfRange.length > 0 && (
                <p className="mt-2 text-[11px]" style={{ color: "var(--warn)" }}>
                  ⚠ {marksOutOfRange.join(", ")} outside the documented normalized 0–1 range. The value is still fed
                  to the model (and will read as strongly out-of-distribution), but it is outside the feature scale
                  the head was trained on.
                </p>
              )}
              <p className="mt-2 text-[11px] text-fg-faint">Served at coarse 1&nbsp;kb atlas resolution → the human K562
                head serves but the outcome-validated flag stays false (exact-site per-locus features, v7.4,
                unlock the validated ρ≈0.57 regime).</p>
            </>
          )}
        </div>
        <div className="mt-4"><Button onClick={run} disabled={busy}>Predict outcome</Button></div>
      </Card>

      <Card title="Predicted outcome" subtitle="A bounded estimate, not a clinical or phenotypic guarantee.">
        {busy ? <Spinner label="Predicting…" /> : error ? <ErrorNote error={error} /> : !res ? (
          <p className="text-sm text-fg-faint">Run a prediction to see the calibrated band.</p>
        ) : (
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
              <Stat label="Relative expression (mechanistic)" value={num(point)} />
              {po?.relative_expression_learned != null && (
                <Stat label="Learned (cell-type head)" value={num(po.relative_expression_learned)} color="var(--brand)" />
              )}
              <Stat label="OOD (response model)" value={res.extrapolating ? "yes " : "no"} color={res.extrapolating ? "var(--warn)" : "var(--ok)"} />
            </div>
            {/* v7.3.14 (tester's exact confusion): this flag is the virtual-cell RESPONSE oracle's own scope
                card (in-distribution cell types + perturbation kinds, every cell type this app's dropdown
                offers is on that list, so it will read "no" through this UI by construction). It is NOT the
                position-effect chromatin model's own OOD signal, that one is the "OOD widen" stat on the position-effect
                card below, and it DOES move (verified: ×1–2 typical, saturating at ×3 under extreme marks). */}
            <p className="text-[11px] leading-relaxed text-fg-faint">
              The headline is the <b>mechanistic</b> estimate, promoter strength × copy number × accessibility
              {res.conditioned_on_preexisting_nab != null ? " × pre-existing-NAb" : ""}. It reacts to <b>promoter</b> and
              <b> delivery vehicle</b>; it is <b>cell-type-agnostic</b> (accessibility is neutral here, the
              cell-type-specific position effect is the learned position-effect head below, which does move with cell type).
              Relative expression is <b>per-copy</b>, so it is independent of cargo size by construction.
            </p>
            <p className="text-[11px] leading-relaxed text-fg-faint">
              <b>OOD (response model)</b> above checks the virtual-cell response oracle's own scope card, a
              documented list of in-distribution cell types and perturbation kinds. Every cell type this app's
              dropdown offers is on that list, so this flag reads "no" through this UI by construction, that's
              expected, not a bug. It is a <b>different</b> signal from the position-effect chromatin model's own
              out-of-distribution check, which is the <b>"OOD widen"</b> stat on the position-effect card below and does
              react to how unusual the supplied chromatin marks are.
            </p>
            {res.feasibility && res.feasibility.buildable === false && (
              <p className="rounded-lg border border-bad/30 bg-bad/5 px-3 py-2 text-[11px] leading-relaxed text-red-300/90">
                <strong>Not buildable as specified.</strong> {res.feasibility.reason}
              </p>
            )}
            <div>
              <div className="mb-1 text-xs uppercase tracking-wide text-fg-faint">Outcome band ({po?.units})</div>
              <ConfidenceBand lo={iv?.[0]} hi={iv?.[1]} point={point} status={status} label="relative expression" />
            </div>
            <p className="rounded-lg border border-warn/25 bg-warn/5 px-3 py-2 text-[11px] leading-relaxed text-fg-dim">
              <strong className="text-warn">Interval kind.</strong> {res.interval_kind}
            </p>
            <div className="flex flex-wrap gap-2">
              {res.stage_h_mode && <Pill color={res.stage_h_mode === "learned_trained_conformal" ? "var(--ok)" : "var(--muted)"}>Serving mode: {res.stage_h_mode.replace(/_/g, " ")}</Pill>}
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

      {/* learned position-effect head provenance + resolution-aware validation state (surfaces when a context is supplied) */}
      {res?.position_effect && <StageHCard pe={res.position_effect} />}
    </div>
  );
}
