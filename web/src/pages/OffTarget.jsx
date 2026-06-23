// Off-Target, cross-writer-family off-target NOMINATION. Rank candidate sites by a real-data, mismatch-calibrated
// risk band (+ the real CRISOT learned score when cached) and ship the assay that would confirm them.
// Conservative by construction: a nomination is a CANDIDATE, never a clearance; the engine abstains without inputs.
import React, { useState } from "react";
import ScoreGuide from "../components/ScoreGuide.jsx";
import { api } from "../api.js";
import { Card, Button, Spinner, ErrorNote, Field, Select } from "../components/ui.jsx";
import { num } from "../lib/format.js";

const FAMILIES = [
  { value: "Cas9", label: "Cas9 nuclease" },
  { value: "Bxb1", label: "Bxb1 serine integrase" },
  { value: "bridge_IS110", label: "bridge recombinase (IS110)" },
];
// prefilled with EMX1 (Tsai 2015 GUIDE-seq) + a few real candidate sites so results render out of the box
const EMX1 = "GAGTCCGAGCAGAAGAAGAAGGG";
const EMX1_CANDS = "GAGTCCGAGCAGAAGAAGAAGGG\nGAGTTAGAGCAGAAGAAGAAGGG\nAAGTCCGAGCAGAAGAAGAAGGG\nGAGTCTAAGCAGAAGAAGAGGGG";

const BAND = { high: "text-red-400", medium: "text-amber-400", low: "text-emerald-400", minimal: "text-fg-faint", uncalibrated: "text-fg-faint" };

export default function OffTarget() {
  const [family, setFamily] = useState("Cas9");
  const [guide, setGuide] = useState(EMX1);
  const [cands, setCands] = useState(EMX1_CANDS);
  const [seq, setSeq] = useState("");
  const [res, setRes] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const isNuclease = family === "Cas9";
  const canRun = isNuclease ? guide.trim() && cands.trim() : seq.trim();

  async function run() {
    if (!canRun) return;
    setBusy(true); setError(null); setRes(null);
    try {
      const body = isNuclease
        ? { writer_family: family, guide, candidate_sites: cands.split(/\s+/).filter(Boolean) }
        : { writer_family: family, sequence: seq };
      setRes(await api.offtarget(body));
    } catch (e) { setError(e); } finally { setBusy(false); }
  }

  const noms = res?.nominations || [];
  const assay = res?.recommended_assay;

  return (
    <div className="space-y-4">
      <ScoreGuide
        intro="A nomination ranks candidate off-target sites by risk; it is NOT a safety clearance. Every candidate ships with the empirical assay that would confirm it."
        items={[
          { term: "Risk band", scale: "high / medium / low / minimal", meaning: "A mismatch-calibrated band from REAL assay data (GUIDE / CIRCLE / CHANGE / SITE-seq active fractions at k mismatches)." },
          { term: "CRISOT score", scale: "0–1, higher = riskier", meaning: "The real learned nuclease off-target score (run on the VM, CC-BY-NC); higher = more likely an active off-target. Shown where cached, else VM-only." },
          { term: "Empirical active fraction", scale: "0–1", meaning: "The measured fraction of candidates at this mismatch count that were validated-active in the calibration assay." },
        ]}
        caveats={[
          "Nomination is not a clearance — it surfaces candidates and the assay that would confirm them.",
          "Chromatin accessibility is a validated ANNOTATION, not folded into the risk score (it added no held-out ranking gain over CRISOT).",
        ]} />

      <Card title="Off-target nomination" subtitle="Rank candidate off-targets with a real-data calibrated risk band, across nucleases, integrases, and bridge recombinases.">
        <div className="grid gap-3 sm:grid-cols-3">
          <Field label="Writer family"><Select value={family} onChange={setFamily} options={FAMILIES} /></Field>
        </div>
        {isNuclease ? (
          <div className="mt-3 grid gap-3">
            <Field label="Guide (protospacer + PAM)"><input className="input font-mono text-xs" value={guide} onChange={(e) => setGuide(e.target.value)} /></Field>
            <Field label="Candidate sites (one per line, from a Cas-OFFinder/genome scan)">
              <textarea className="input font-mono text-xs h-28" value={cands} onChange={(e) => setCands(e.target.value)} />
            </Field>
          </div>
        ) : (
          <div className="mt-3">
            <Field label="Locus / target sequence (scanned for cryptic pseudo-attB)">
              <textarea className="input font-mono text-xs h-28" value={seq} onChange={(e) => setSeq(e.target.value)} placeholder="paste a genomic region…" />
            </Field>
          </div>
        )}
        <div className="mt-4 flex items-center gap-3">
          <Button onClick={run} disabled={busy || !canRun}>Nominate off-targets</Button>
          {!canRun && <span className="text-[11px] text-fg-faint">{isNuclease ? "Enter a guide and at least one candidate site." : "Paste a locus sequence to scan."}</span>}
        </div>
      </Card>

      <Card>
        <p className="text-xs text-amber-300/90"> Nomination is <b>not</b> a safety clearance, every candidate ships with the empirical assay that would confirm it. The CRISOT learned score is run on the VM (CC-BY-NC); only derived scores are cached.</p>
      </Card>

      {busy && <Card><Spinner label="Scoring candidate off-targets…" /></Card>}
      {error && <Card><ErrorNote error={error} /></Card>}

      {res && res.abstain && (
        <Card title="Abstained (no fabrication)"><p className="text-sm text-fg-dim">{res.note}</p></Card>
      )}

      {res && !res.abstain && isNuclease && (
        <Card title={`Ranked off-target candidates`} subtitle={`${res.n_candidates} candidates · risk calibrated on ${res.assay_calibration} · ranked by the real CRISOT score where cached`}>
          {res.bench && (
            <p className="mb-2 text-[11px] text-fg-faint">Bench (held-out guides): CRISOT AUPRC {num(res.bench.crisot_auprc)} vs homology {num(res.bench.homology_auprc)}, the learned predictor beats homology (CI {JSON.stringify(res.bench.gap_ci95)}).</p>
          )}
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead><tr className="border-b border-line text-left text-[11px] uppercase tracking-wide text-fg-faint">
                <th className="py-2 pr-3">Site</th><th className="py-2 pr-3">Mismatch</th>
                <th className="py-2 pr-3">Empirical active</th><th className="py-2 pr-3">Risk</th><th className="py-2">CRISOT</th></tr></thead>
              <tbody>
                {noms.map((n, i) => (
                  <tr key={i} className="border-b border-line/50">
                    <td className="py-2 pr-3 font-mono text-xs">{n.site?.slice(0, 23)}</td>
                    <td className="py-2 pr-3 tabular-nums">{n.n_mismatch}</td>
                    <td className="py-2 pr-3 tabular-nums">{n.empirical_active_fraction == null ? "n/a" : num(n.empirical_active_fraction)}</td>
                    <td className={`py-2 pr-3 font-medium ${BAND[n.risk_band] || ""}`}>{n.risk_band}</td>
                    <td className="py-2 tabular-nums text-brand">{n.crisot_score == null ? "VM-only" : num(n.crisot_score)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {res && !res.abstain && !isNuclease && (
        <Card title="Cryptic pseudo-attB candidates" subtitle={`${res.n_candidates || 0} candidates · core ${res.att_core || ""} · ${res.validating_assay || ""}`}>
          {noms.length === 0 ? <p className="text-sm text-fg-faint">No cryptic pseudo-attB sites found in the supplied sequence.</p> : (
            <ol className="space-y-2">
              {noms.map((n, i) => (
                <li key={i} className="rounded-lg border border-line bg-ink-900 p-3 text-sm">
                  <span className="font-mono text-xs">{n.site}</span>
                  <span className="ml-3 text-[11px] text-fg-dim">pos {n.pos} · arm mismatches {n.arm_mismatch}</span>
                </li>
              ))}
            </ol>
          )}
        </Card>
      )}

      {assay && assay.available && (
        <Card title="Recommended validation assay" subtitle={assay.writer_class}>
          <ul className="space-y-1 text-sm">
            {(assay.recommended || []).map((a, i) => (
              <li key={i}><b>{a.assay}</b> <span className="text-fg-dim">({a.setting})</span>, {a.use}</li>
            ))}
          </ul>
          <p className="mt-2 text-[11px] text-fg-faint">{assay.strategy}</p>
          {assay.note && <p className="mt-1 text-[11px] text-amber-300/80">{assay.note}</p>}
        </Card>
      )}
    </div>
  );
}
