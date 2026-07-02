// Off-Target FINDER (v7.2) — genome-wide, per-writer-mechanism. A real off-target tool takes a guide/target and
// returns the genome-wide off-target set (like CRISPOR/CHOPCHOP), applying the CORRECT mechanism per writer class:
// nuclease cleavage, integrase pseudo-attP, bridge target-specificity, CAST guide+untargeted, PASTE composition.
// Each carries a TRUTHFUL status (validated / semi-validated / mechanism-based-unvalidated). Enumeration runs on
// the VM; the app replays the cache or abstains. Nomination is a CANDIDATE, never a clearance.
import React, { useEffect, useState } from "react";
import ScoreGuide from "../components/ScoreGuide.jsx";
import { api } from "../api.js";
import { Card, Button, Spinner, ErrorNote, Field, Select, Pill } from "../components/ui.jsx";
import { num } from "../lib/format.js";

const FAMILIES = [
  { value: "Cas9", label: "Cas9 nuclease — genome-wide finder (validated)" },
  { value: "Bxb1", label: "Bxb1 serine integrase — pseudo-attP scan (semi-validated)" },
  { value: "bridge_IS110", label: "bridge recombinase IS110 — TBL scan (unvalidated)" },
  { value: "ShCAST", label: "ShCAST (Type V-K) — guide + untargeted (unvalidated)" },
  { value: "PASTE", label: "PASTE / PASSIGE — nuclease + integrase (composite)" },
];
const EMX1 = "GAGTCCGAGCAGAAGAAGAAGGG";
const BAND = { high: "text-red-400", medium: "text-amber-400", low: "text-emerald-400", minimal: "text-fg-faint", uncalibrated: "text-fg-faint" };
const STATUS_COLOR = { validated: "var(--ok)", semi_validated: "var(--warn)", mechanism_based_unvalidated: "var(--warn)", composite: "var(--warn)" };
const fmtStatus = (s) => String(s || "").replace(/_/g, " ");
function StatusBadge({ status }) {
  return <Pill color={STATUS_COLOR[status] || "var(--muted)"}>{fmtStatus(status)}</Pill>;
}

export default function OffTarget() {
  const [family, setFamily] = useState("Cas9");
  const [guide, setGuide] = useState(EMX1);
  const [targetCore, setTargetCore] = useState("");
  const [cached, setCached] = useState([]);
  const [res, setRes] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => { api.offtargetEnumerated().then((r) => setCached(r.guides || [])).catch(() => {}); }, []);

  const needsGuide = family === "Cas9" || family === "PASTE";
  const isCast = family === "ShCAST";
  const isBridge = family === "bridge_IS110";
  const canRun = needsGuide ? guide.trim().length >= 20 : true;

  async function run() {
    if (!canRun) return;
    setBusy(true); setError(null); setRes(null);
    try {
      const body = { writer_family: family };
      if (family === "Cas9") { body.enzyme = "SpCas9"; body.guide = guide; }
      else if (family === "PASTE") body.guide = guide;
      else if (isCast) { body.enzyme = "ShCAST"; if (guide.trim()) body.guide = guide.trim(); }
      else if (isBridge && targetCore.trim()) body.target_core = targetCore.trim();
      setRes(await api.offtarget(body));
    } catch (e) { setError(e); } finally { setBusy(false); }
  }

  const assay = res?.recommended_assay;

  return (
    <div className="space-y-4">
      <ScoreGuide
        intro="A genome-wide off-target FINDER that applies the CORRECT mechanism for each writer class and labels each with a truthful validation status. A nomination is a CANDIDATE, never a clearance; every result ships with the empirical assay that would confirm it."
        items={[
          { term: "Per-mechanism status", scale: "validated / semi / unvalidated", meaning: "Nuclease is VALIDATED (CRISOT beats homology on 4 assays; enumeration recovers the documented off-target set). Integrase is SEMI-VALIDATED (documented pseudosites, partial). Bridge & CAST are MECHANISM-BASED, UNVALIDATED — no genome-wide cellular off-target assay exists for them, and the tool says so." },
          { term: "Finder vs scorer", scale: "genome-wide", meaning: "The engine enumerates candidates itself over GRCh38 (Cas-OFFinder), then scores them — like CRISPOR's search step." },
          { term: "Nuclease risk / CRISOT", scale: "band + 0–1", meaning: "A mismatch-calibrated risk band from real assay data, plus the real learned CRISOT off-target score (VM)." },
          { term: "CAST untargeted", scale: "tier", meaning: "The guide-INDEPENDENT untargeted-transposition background — the distinctive CAST off-target mode (Type V-K high, Type I-F low), a documented per-system property." },
        ]}
        caveats={[
          "Enumeration runs on the VM; the app replays the committed cache or abstains for a novel input — it never fabricates sites.",
          "You cannot make bridge/CAST off-target 'work like CRISPOR' — that needs validation data the field does not yet have for these ~2-year-old technologies. The honest answer is a mechanism-based scan with a truthful 'unvalidated' label.",
          "The engine nominates and ranks; it does NOT clear a design — wet-lab confirmation with the recommended assay is required.",
        ]} />

      <Card title="Off-target finder" subtitle="Pick a writer class; the correct off-target mechanism and status are applied automatically.">
        <div className="grid gap-3 sm:grid-cols-2">
          <Field label="Writer class"><Select value={family} onChange={(v) => { setFamily(v); setRes(null); }} options={FAMILIES} /></Field>
        </div>
        {needsGuide && (
          <div className="mt-3 grid gap-3">
            <Field label={family === "PASTE" ? "pegRNA spacer (protospacer + PAM)" : "Guide (protospacer + PAM, SpCas9 NGG)"}>
              <input className="input font-mono text-xs" value={guide} onChange={(e) => setGuide(e.target.value.toUpperCase())} />
            </Field>
            {cached.length > 0 && (
              <div className="text-[11px] text-fg-faint">Cached guides (instant genome-wide replay):{" "}
                {cached.map((c) => (
                  <button key={c.guide} onClick={() => setGuide(c.guide + "GGG")}
                          className="mr-1 mb-1 rounded border border-line px-1.5 py-0.5 font-mono hover:border-brand/50 hover:text-brand">{c.name}</button>
                ))}
              </div>
            )}
          </div>
        )}
        {isCast && (
          <div className="mt-3"><Field label="crRNA spacer (optional — for guide-directed sites; the untargeted background always shows)">
            <input className="input font-mono text-xs" value={guide} onChange={(e) => setGuide(e.target.value.toUpperCase())} placeholder="optional Cas12k spacer…" /></Field></div>
        )}
        {isBridge && (
          <div className="mt-3"><Field label="Bridge-RNA target core (optional — a genome scan needs the VM genome; otherwise the engine explains how to run it)">
            <input className="input font-mono text-xs" value={targetCore} onChange={(e) => setTargetCore(e.target.value.toUpperCase())} placeholder="bipartite ~14-nt target (central CT)…" /></Field></div>
        )}
        <div className="mt-4 flex items-center gap-3">
          <Button onClick={run} disabled={busy || !canRun}>Find off-targets</Button>
          {needsGuide && !canRun && <span className="text-[11px] text-fg-faint">Enter a ≥20-nt guide (or pick a cached one).</span>}
        </div>
      </Card>

      {busy && <Card><Spinner label="Finding off-targets…" /></Card>}
      {error && <Card><ErrorNote error={error} /></Card>}

      {/* NUCLEASE finder */}
      {res && res.family === "nuclease" && (res.abstain ? (
        <Card title="Abstained (no fabrication)"><p className="text-sm text-fg-dim">{res.note}</p>
          {res.cached_guides?.length > 0 && <p className="mt-2 text-[11px] text-fg-faint">Cached: {res.cached_guides.join(", ")}.</p>}</Card>
      ) : (
        <Card title="Genome-wide off-targets" subtitle={`${res.n_sites_genome_wide} sites · ${res.n_on_target} on-target · ${res.n_offtargets} off-targets · source ${res.source}`}>
          <div className="mb-2 flex items-center gap-2"><StatusBadge status={res.status} />
            {res.bench && <span className="text-[11px] text-fg-faint">CRISOT AUPRC {num(res.bench.crisot_auprc)} vs homology {num(res.bench.homology_auprc)} (beats homology).</span>}</div>
          <div className="overflow-x-auto"><table className="w-full text-sm">
            <thead><tr className="border-b border-line text-left text-[11px] uppercase tracking-wide text-fg-faint">
              <th className="py-2 pr-3">Locus</th><th className="py-2 pr-3">Str</th><th className="py-2 pr-3">MM</th><th className="py-2 pr-3">Emp. active</th><th className="py-2 pr-3">Risk</th><th className="py-2">CRISOT</th></tr></thead>
            <tbody>{(res.nominations || []).map((n, i) => (
              <tr key={i} className={`border-b border-line/50 ${n.n_mismatch === 0 ? "bg-emerald-500/5" : ""}`}>
                <td className="py-2 pr-3 font-mono text-xs">{n.chrom}:{n.position}{n.n_mismatch === 0 ? " (on-target)" : ""}</td>
                <td className="py-2 pr-3 tabular-nums">{n.strand}</td><td className="py-2 pr-3 tabular-nums">{n.n_mismatch}</td>
                <td className="py-2 pr-3 tabular-nums">{n.empirical_active_fraction == null ? "n/a" : num(n.empirical_active_fraction)}</td>
                <td className={`py-2 pr-3 font-medium ${BAND[n.risk_band] || ""}`}>{n.risk_band}</td>
                <td className="py-2 tabular-nums text-brand">{n.crisot_score == null ? "VM-only" : num(n.crisot_score)}</td></tr>))}</tbody>
          </table></div>
          <p className="mt-2 text-[11px] text-fg-faint">{res.method}</p>
        </Card>
      ))}

      {/* INTEGRASE pseudo-attP */}
      {res && res.family === "serine_integrase" && (
        <Card title="Pseudo-attP" subtitle={res.abstain ? "" : `core ${res.att_core} · ${res.integrase}`}>
          <div className="mb-2"><StatusBadge status={res.status} /></div>
          {/* the sealed PhiC31 recall benchmark verdict (the key honest finding) — shown for both integrases */}
          {res.sealed_recall_benchmark && (
            <p className="mb-2 rounded border border-warn/25 bg-warn/5 px-3 py-2 text-[11px] leading-relaxed text-amber-300/80">
              <b>Sealed recall benchmark:</b> {res.sealed_recall_benchmark.verdict}
            </p>
          )}
          {res.abstain ? (
            <p className="text-sm text-fg-dim">{res.note}</p>
          ) : res.documented_pseudo_attP ? (<>
            <p className="mb-2 text-[11px] text-fg-faint">Verified documented human pseudo-attP ({res.documented_source}, DOI {res.documented_doi}):</p>
            <div className="overflow-x-auto"><table className="w-full text-sm">
              <thead><tr className="border-b border-line text-left text-[11px] uppercase tracking-wide text-fg-faint">
                <th className="py-2 pr-3">Site</th><th className="py-2 pr-3">GenBank</th><th className="py-2">Chrom</th></tr></thead>
              <tbody>{res.documented_pseudo_attP.map((s, i) => (
                <tr key={i} className="border-b border-line/50"><td className="py-2 pr-3 font-medium">{s.name}</td>
                  <td className="py-2 pr-3 font-mono text-xs">{s.genbank}</td><td className="py-2">{s.chrom}</td></tr>))}</tbody>
            </table></div>
            <p className="mt-2 text-[11px] text-fg-faint">{res.method}</p>
          </>) : (<>
            {res.specificity_note && <p className="mb-2 text-[11px] text-fg-faint">{res.specificity_note}</p>}
            <p className="mb-2 text-[11px] text-fg-faint">{res.n_sites_genome_wide} genome-wide similarity candidate(s):</p>
            <div className="overflow-x-auto"><table className="w-full text-sm">
              <thead><tr className="border-b border-line text-left text-[11px] uppercase tracking-wide text-fg-faint">
                <th className="py-2 pr-3">Locus</th><th className="py-2 pr-3">Str</th><th className="py-2 pr-3">Att mismatch</th><th className="py-2">Arm similarity</th></tr></thead>
              <tbody>{(res.nominations || []).map((n, i) => (
                <tr key={i} className="border-b border-line/50"><td className="py-2 pr-3 font-mono text-xs">{n.chrom}:{n.position}</td>
                  <td className="py-2 pr-3 tabular-nums">{n.strand}</td><td className="py-2 pr-3 tabular-nums">{n.n_mismatch}</td>
                  <td className="py-2 tabular-nums text-brand">{num(n.arm_similarity)}</td></tr>))}</tbody>
            </table></div>
            <p className="mt-2 text-[11px] text-fg-faint">{res.method}</p>
          </>)}
        </Card>
      )}

      {/* BRIDGE */}
      {res && res.family === "bridge" && (
        <Card title="Bridge off-target" subtitle={`IS110 target-specificity scan · ${res.ranker}`}>
          <div className="mb-2"><StatusBadge status={res.status} /></div>
          {res.engine?.status === "scanned" ? (
            <p className="text-sm text-fg-dim">{res.engine.n_candidates} candidate pseudosites ({res.engine.n_exact_matches} exact). Ranked by the measured DMS specificity.</p>
          ) : (
            <p className="text-sm text-fg-dim">{res.engine?.note || "Provide a bridge-RNA target core + the VM genome for a genome-wide scan."}</p>
          )}
          <p className="mt-2 rounded border border-warn/25 bg-warn/5 px-3 py-2 text-[11px] leading-relaxed text-amber-300/80">{res.no_ground_truth_disclosure}</p>
        </Card>
      )}

      {/* CAST */}
      {res && res.family === "cast" && (
        <Card title={`CAST off-target · ${res.system} (Type ${res.cast_type})`}>
          <div className="mb-2"><StatusBadge status={res.status} /></div>
          <div className="rounded-lg border border-line bg-ink-900 p-3">
            <div className="flex flex-wrap items-center gap-2 text-sm"><span className="font-semibold text-fg">Guide-independent untargeted transposition</span>
              <Pill color={res.untargeted_background.tier === "high" ? "var(--bad)" : res.untargeted_background.tier === "low" ? "var(--ok)" : "var(--warn)"}>{res.untargeted_background.tier}</Pill>
              {res.untargeted_background.at_biased && <span className="chip">AT-biased</span>}</div>
            <p className="mt-1.5 text-[11px] text-fg-dim">{res.untargeted_background.fidelity_note}</p>
            <p className="mt-1 text-[11px] text-fg-faint">{res.untargeted_background.note}</p>
          </div>
          {res.guide_directed && (res.guide_directed.available
            ? <p className="mt-2 text-sm text-fg-dim">Guide-directed: {res.guide_directed.n_offtargets} off-targets ({res.guide_directed.source}).</p>
            : <p className="mt-2 text-[11px] text-fg-faint">Guide-directed: {res.guide_directed.note}</p>)}
          <p className="mt-2 text-[11px] text-fg-faint">{res.method}</p>
        </Card>
      )}

      {/* PASTE composite */}
      {res && res.family === "paste" && (
        <Card title="PASTE off-target (composite)" subtitle="Two independent components: the Cas9-nickase and the installed-att integrase.">
          <div className="mb-2 flex items-center gap-2"><StatusBadge status={res.status} /></div>
          <div className="grid gap-3 sm:grid-cols-2">
            <div className="rounded-lg border border-line bg-ink-900 p-3">
              <div className="mb-1 flex items-center gap-2 text-sm"><span className="font-semibold text-fg">Nuclease (nickase)</span><StatusBadge status={res.component_statuses.nuclease_component} /></div>
              <p className="text-[11px] text-fg-dim">{res.nuclease_component.abstain ? res.nuclease_component.note : `${res.nuclease_component.n_offtargets} genome-wide off-targets for the pegRNA spacer.`}</p>
            </div>
            <div className="rounded-lg border border-line bg-ink-900 p-3">
              <div className="mb-1 flex items-center gap-2 text-sm"><span className="font-semibold text-fg">Integrase (installed att)</span><StatusBadge status={res.component_statuses.integrase_component} /></div>
              <p className="text-[11px] text-fg-dim">{res.integrase_component.abstain ? res.integrase_component.note : `${res.integrase_component.n_sites_genome_wide} genome-wide pseudo-attP candidates.`}</p>
            </div>
          </div>
          <p className="mt-2 text-[11px] text-amber-300/80">{res.confirm_assay.note}</p>
        </Card>
      )}

      {assay && assay.available && (
        <Card title="Recommended validation assay" subtitle={assay.writer_class}>
          <ul className="space-y-1 text-sm">{(assay.recommended || []).map((a, i) => (
            <li key={i}><b>{a.assay}</b> <span className="text-fg-dim">({a.setting})</span>, {a.use}</li>))}</ul>
          <p className="mt-2 text-[11px] text-fg-faint">{assay.strategy}</p>
          {assay.note && <p className="mt-1 text-[11px] text-amber-300/80">{assay.note}</p>}
        </Card>
      )}
    </div>
  );
}
