// Off-Target FINDER (v7.2). A real off-target tool takes a GUIDE and returns the genome-wide off-target set —
// like CRISPOR/CHOPCHOP — instead of scoring sites you supply. Enumeration (Cas-OFFinder over GRCh38) is heavy
// and runs on the VM; this surface replays the committed coordinate cache for the canonical guides, or abstains
// honestly for a novel one (a VM scan). Nomination is a CANDIDATE, never a clearance.
import React, { useEffect, useState } from "react";
import ScoreGuide from "../components/ScoreGuide.jsx";
import { api } from "../api.js";
import { Card, Button, Spinner, ErrorNote, Field, Select, Pill } from "../components/ui.jsx";
import { num } from "../lib/format.js";

const FAMILIES = [
  { value: "Cas9", label: "Cas9 nuclease (genome-wide finder)" },
  { value: "Bxb1", label: "Bxb1 serine integrase (pseudo-attB scan)" },
  { value: "bridge_IS110", label: "bridge recombinase (IS110)" },
];
const EMX1 = "GAGTCCGAGCAGAAGAAGAAGGG"; // a cached canonical guide (Tsai 2015 GUIDE-seq) — works out of the box
const BAND = { high: "text-red-400", medium: "text-amber-400", low: "text-emerald-400", minimal: "text-fg-faint", uncalibrated: "text-fg-faint" };
const STATUS = { validated: "var(--ok)", semi_validated: "var(--warn)", mechanism_based_unvalidated: "var(--warn)" };

export default function OffTarget() {
  const [family, setFamily] = useState("Cas9");
  const [guide, setGuide] = useState(EMX1);
  const [seq, setSeq] = useState("");
  const [cached, setCached] = useState([]);
  const [res, setRes] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const isNuclease = family === "Cas9";
  const canRun = isNuclease ? guide.trim().length >= 20 : seq.trim();

  useEffect(() => { api.offtargetEnumerated().then((r) => setCached(r.guides || [])).catch(() => {}); }, []);

  async function run() {
    if (!canRun) return;
    setBusy(true); setError(null); setRes(null);
    try {
      const body = isNuclease
        ? { writer_family: "Cas9", enzyme: "SpCas9", guide }               // finder: guide -> genome-wide set
        : { writer_family: family, sequence: seq };
      setRes(await api.offtarget(body));
    } catch (e) { setError(e); } finally { setBusy(false); }
  }

  const noms = res?.nominations || [];
  const assay = res?.recommended_assay;

  return (
    <div className="space-y-4">
      <ScoreGuide
        intro="An off-target FINDER: give it a guide and it returns the genome-wide off-target set (coordinates, mismatches, risk, and the real CRISOT score) — the way CRISPOR/CHOPCHOP work — not a list of sites you supply. A nomination is a CANDIDATE, never a clearance; every result ships with the empirical assay that would confirm it."
        items={[
          { term: "Finder vs scorer", scale: "genome-wide", meaning: "The engine ENUMERATES every genomic site within the mismatch tolerance itself (Cas-OFFinder over GRCh38), then scores + ranks them. Previously it only scored candidate sites you pasted in." },
          { term: "Risk band", scale: "high / medium / low / minimal", meaning: "A mismatch-calibrated band from REAL assay data (GUIDE / CIRCLE / CHANGE / SITE-seq active fractions at k mismatches)." },
          { term: "CRISOT score", scale: "0–1, higher = riskier", meaning: "The real learned nuclease off-target score (VM, CC-BY-NC). Shown where cached; a novel (guide, site) pair is VM-only." },
          { term: "Per-mechanism status", scale: "validated / semi / unvalidated", meaning: "Nuclease is validated (CRISOT beats homology on 4 assays; enumeration recovers the documented off-target set). Integrase is semi-validated; bridge/CAST have no genome-wide ground truth and say so." },
        ]}
        caveats={[
          "Enumeration runs on the VM; this page replays the committed cache for the canonical guides, or abstains for a novel guide (a VM scan) — it never fabricates sites.",
          "Chromatin accessibility is a validated ANNOTATION, not folded into the risk score (it added no held-out ranking gain over CRISOT).",
          "The engine nominates and ranks; it does NOT clear a design — wet-lab confirmation with the recommended assay is required.",
        ]} />

      <Card title="Off-target finder" subtitle="Give a guide; get the genome-wide ranked off-target set. Nucleases enumerate over GRCh38; integrases scan a supplied locus for cryptic pseudo-attB.">
        <div className="grid gap-3 sm:grid-cols-3">
          <Field label="Writer family"><Select value={family} onChange={setFamily} options={FAMILIES} /></Field>
        </div>
        {isNuclease ? (
          <div className="mt-3 grid gap-3">
            <Field label="Guide (protospacer + PAM, SpCas9 NGG)">
              <input className="input font-mono text-xs" value={guide} onChange={(e) => setGuide(e.target.value.toUpperCase())} />
            </Field>
            {cached.length > 0 && (
              <div className="text-[11px] text-fg-faint">
                Cached guides (replay the genome-wide scan instantly):{" "}
                {cached.map((c) => (
                  <button key={c.guide} onClick={() => setGuide(c.guide + "GGG")}
                          className="mr-1 mb-1 rounded border border-line px-1.5 py-0.5 font-mono hover:border-brand/50 hover:text-brand">
                    {c.name}
                  </button>
                ))}
              </div>
            )}
          </div>
        ) : (
          <div className="mt-3">
            <Field label="Locus / target sequence (scanned for cryptic pseudo-attB)">
              <textarea className="input font-mono text-xs h-28" value={seq} onChange={(e) => setSeq(e.target.value)} placeholder="paste a genomic region…" />
            </Field>
          </div>
        )}
        <div className="mt-4 flex items-center gap-3">
          <Button onClick={run} disabled={busy || !canRun}>{isNuclease ? "Find genome-wide off-targets" : "Scan for pseudo-attB"}</Button>
          {!canRun && <span className="text-[11px] text-fg-faint">{isNuclease ? "Enter a ≥20-nt guide (or pick a cached one)." : "Paste a locus sequence to scan."}</span>}
        </div>
      </Card>

      {busy && <Card><Spinner label="Enumerating genome-wide off-targets…" /></Card>}
      {error && <Card><ErrorNote error={error} /></Card>}

      {res && res.abstain && (
        <Card title="Abstained (no fabrication)">
          <p className="text-sm text-fg-dim">{res.note}</p>
          {res.cached_guides?.length > 0 && (
            <p className="mt-2 text-[11px] text-fg-faint">Guides with a cached genome-wide scan: {res.cached_guides.join(", ")}. A novel guide's scan runs on the VM.</p>
          )}
        </Card>
      )}

      {res && res.mode === "finder" && !res.abstain && (
        <Card title="Genome-wide off-targets"
              subtitle={`${res.n_sites_genome_wide} sites over GRCh38 · ${res.n_on_target} on-target · ${res.n_offtargets} off-targets · source: ${res.source}`}>
          <div className="mb-2 flex flex-wrap items-center gap-2 text-[11px]">
            <Pill color={STATUS[res.status] || "var(--muted)"}>{String(res.status).replace(/_/g, " ")}</Pill>
            {res.bench && <span className="text-fg-faint">Bench: CRISOT AUPRC {num(res.bench.crisot_auprc)} vs homology {num(res.bench.homology_auprc)} (beats homology, CI excludes 0).</span>}
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead><tr className="border-b border-line text-left text-[11px] uppercase tracking-wide text-fg-faint">
                <th className="py-2 pr-3">Locus</th><th className="py-2 pr-3">Strand</th><th className="py-2 pr-3">Mismatch</th>
                <th className="py-2 pr-3">Empirical active</th><th className="py-2 pr-3">Risk</th><th className="py-2">CRISOT</th></tr></thead>
              <tbody>
                {noms.map((n, i) => (
                  <tr key={i} className={`border-b border-line/50 ${n.n_mismatch === 0 ? "bg-emerald-500/5" : ""}`}>
                    <td className="py-2 pr-3 font-mono text-xs">{n.chrom}:{n.position}{n.n_mismatch === 0 ? " (on-target)" : ""}</td>
                    <td className="py-2 pr-3 tabular-nums">{n.strand}</td>
                    <td className="py-2 pr-3 tabular-nums">{n.n_mismatch}</td>
                    <td className="py-2 pr-3 tabular-nums">{n.empirical_active_fraction == null ? "n/a" : num(n.empirical_active_fraction)}</td>
                    <td className={`py-2 pr-3 font-medium ${BAND[n.risk_band] || ""}`}>{n.risk_band}</td>
                    <td className="py-2 tabular-nums text-brand">{n.crisot_score == null ? "VM-only" : num(n.crisot_score)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="mt-2 text-[11px] text-fg-faint">{res.method}</p>
        </Card>
      )}

      {res && !res.abstain && res.mode !== "finder" && (
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
