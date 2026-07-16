// Guardian, the biosecurity / dual-use screen. clear / flag / escalate / refuse, with the reason and an audit
// note. This is the orthogonal safety axis: a refused design is never scored on efficacy.
import React, { useEffect, useState } from "react";
import WhatYouGet from "../components/WhatYouGet.jsx";
import { api } from "../api.js";
import { Card, Button, Spinner, ErrorNote, Pill } from "../components/ui.jsx";
import DesignForm, { DEFAULT_DESIGN } from "../components/DesignForm.jsx";
import SafetyBadge from "../components/SafetyBadge.jsx";
import ScoreGuide from "../components/ScoreGuide.jsx";
import { num } from "../lib/format.js";

const PRESETS = [
  { label: "Benign, human Factor IX", patch: { cargo_function: "human factor IX", pfam_domains: [] } },
  { label: "Hazard, ricin-like RIP", patch: { cargo_function: "ricin-like ribosome-inactivating protein", pfam_domains: ["PF00161"] } },
  { label: "Dual-use, toxin domain", patch: { cargo_function: "cholera-like enterotoxin subunit", pfam_domains: ["PF01375"] } },
];

const CM_STATUS_COLOR = { Pass: "var(--ok)", Warning: "var(--warn)", Flag: "var(--bad)" };
const SECUREDNA_COLOR = { pass: "var(--ok)", review: "var(--warn)", deny: "var(--bad)" };

export default function Guardian() {
  const [design, setDesign] = useState({ ...DEFAULT_DESIGN, actor: "web" });
  const [res, setRes] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const [conc, setConc] = useState(null); // the fixed labelled-probe-set concordance benchmark (v6.12)

  useEffect(() => { api.safetyConcordance().then(setConc).catch(() => {}); }, []);

  async function run(d = design) {
    setBusy(true); setError(null);
    try { setRes(await api.safety(d)); } catch (e) { setError(e); setRes(null); } finally { setBusy(false); }
  }

  return (
    <div className="space-y-4">
      <WhatYouGet
        intro="Submit a design or a stated cargo function and get a biosecurity / dual-use decision, clear, flag, escalate or refuse, with the reason and an audit note. This is the safety gate that runs first; a refused design is never scored."
        features={[
          { name: "Biosecurity decision", tells: "is the design's function a controlled dual-use hazard?", output: "clear / flag / escalate / refuse" },
          { name: "Signature match", tells: "which function / family / taxon / sequence-domain signature it hit", output: "the matched control-list category (a public Pfam profile match, never a hazard sequence itself)" },
          { name: "Standards alignment", tells: "does this decision agree with the Common Mechanism / SecureDNA vocabulary?", output: "ScreenStatus + pass/deny outcome" },
          { name: "Standards concordance", tells: "does the Guardian agree with the Common Mechanism over a labelled probe set?", output: "N/N concordant (fixed benchmark)" },
          { name: "Audit note", tells: "a tamper-evident record of the screen", output: "hash-chained audit entry" },
        ]}
        example="A Factor IX gene therapy → clear. A ricin toxin cargo → refuse, no design scored, with the Select-Agent / control-list category cited, reframing the request cannot flip a refuse to a clear."
      />
      <ScoreGuide
        intro="The Guardian is a biosecurity / dual-use screen, not a score. It returns one of four decisions on the design's function, family, taxon, and (if a Cargo sequence is given) sequence-domain signatures."
        items={[
          { term: "Decision", scale: "clear / flag / escalate / refuse", meaning: "clear = no dual-use signal; flag / escalate = route to a human with the reason; refuse = hazardous, the design stops here and is never scored on efficacy." },
          { term: "Hit severity", scale: "high / medium", meaning: "Per-signature severity, each carrying its signature id and the control reference it matched." },
        ]}
        caveats={[
          "Function / family / taxon signatures, plus a local Pfam/HMMER domain screen over a submitted Cargo sequence, scoped to the same curated toxin-family list, never a hazard sequence itself.",
          "Necessary, not sufficient: a downstream, full-scale sequence screen (BioFirewall) is the complementary check.",
        ]} />
      <div className="grid gap-4 lg:grid-cols-2">
      <Card title="Screen a design" subtitle="The Guardian inspects the cargo function and domains for hazard signal.">
        <div className="mb-3 flex flex-wrap gap-2">
          {PRESETS.map((p) => (
            <button key={p.label} onClick={() => { const d = { ...design, ...p.patch }; setDesign(d); run(d); }}
              className="rounded-lg border border-line bg-ink-900 px-2.5 py-1 text-xs text-fg-dim hover:border-brand/40 hover:text-fg">
              {p.label}
            </button>
          ))}
        </div>
        <DesignForm design={design} onChange={setDesign} />
        <div className="mt-4"><Button onClick={() => run()} disabled={busy}>Run biosecurity screen</Button></div>
      </Card>

      <Card title="Guardian verdict" subtitle="Refusal is a feature: hazardous designs stop here.">
        {busy ? <Spinner label="Screening…" /> : error ? <ErrorNote error={error} /> : !res ? (
          <p className="text-sm text-fg-faint">Pick a preset or screen your own design.</p>
        ) : (
          <div className="space-y-3">
            <SafetyBadge decision={res.decision} reason={res.reason} />
            {/* v7.3.11: an empty Cargo function box (+ no domains/taxon) also decides "clear" -- nothing was
                submitted, so nothing could be checked. Without this, that's indistinguishable from a real
                benign design being screened and passing. */}
            {res.provenance?.declared_signal === false && (
              <p className="rounded-lg border px-3 py-2 text-xs" style={{ borderColor: "var(--warn)55", background: "var(--warn)12", color: "var(--warn)" }}>
                ⚠ Nothing was screened, no cargo function, sequence, domain tag, or taxon was declared. "Clear"
                here means there was no input to check, not a verified-safe result.
              </p>
            )}
            {(res.hits || []).length === 0 ? (
              <p className="text-xs text-fg-faint">No hazard hits, the screen found no dual-use signal in the cargo.</p>
            ) : (
              <ul className="space-y-2">
                {res.hits.map((h, i) => (
                  <li key={i} className="rounded-lg border border-warn/30 bg-warn/5 p-3 text-xs">
                    <div className="flex items-center justify-between gap-2">
                      <span className="font-medium text-fg">{h.detail || h.kind}</span>
                      <Pill color={h.severity === "high" ? "var(--bad)" : "var(--warn)"}>{h.severity}</Pill>
                    </div>
                    <div className="mt-1 flex flex-wrap gap-2 text-[11px] text-fg-dim">
                      {h.kind && <span>kind: {h.kind}</span>}
                      {h.provenance?.signature_id && <span>sig: {h.provenance.signature_id}</span>}
                      {h.provenance?.control_ref && <span>control: {h.provenance.control_ref}</span>}
                      {h.evidence?.pfam_accession && <span>Pfam: {h.evidence.pfam_accession}</span>}
                      {h.evidence?.bit_score != null && <span>bit score: {h.evidence.bit_score} (vs. gathering cutoff)</span>}
                    </div>
                  </li>
                ))}
              </ul>
            )}
            {res.provenance?.registry_version && (
              <p className="text-[11px] text-fg-faint">Registry: <span className="font-mono">{res.provenance.registry_version}</span></p>
            )}
            {/* v7.3.8: does this specific decision agree with community standards? (in-design concordance, not a certification) */}
            {res.standards && (
              <div className="rounded-lg border border-line bg-ink-900 p-3">
                <div className="mb-1.5 text-[11px] font-semibold uppercase tracking-wide text-fg-faint">Standards alignment</div>
                <div className="flex flex-wrap gap-2">
                  <Pill color={CM_STATUS_COLOR[res.standards.common_mechanism_status] || "var(--muted)"}>
                    Common Mechanism: {res.standards.common_mechanism_status}
                  </Pill>
                  <Pill color={SECUREDNA_COLOR[res.standards.securedna_outcome] || "var(--muted)"}>
                    SecureDNA: {res.standards.securedna_outcome}
                  </Pill>
                </div>
                <p className="mt-1.5 text-[11px] leading-relaxed text-fg-faint">{res.standards.note}</p>
              </div>
            )}
          </div>
        )}
      </Card>
      </div>

      {/* v7.3.8: the labelled-probe-set concordance benchmark (v6.12), was computed but had no UI/API surface */}
      <Card title="Standards concordance" subtitle="Does the Guardian's decision agree with the Common Mechanism's expected status, over a labelled probe set?">
        {!conc ? (
          <p className="text-sm text-fg-faint">Loading…</p>
        ) : (
          <div className="space-y-2">
            <div className="flex flex-wrap items-center gap-3">
              <Pill color={conc.n_concordant === conc.n ? "var(--ok)" : "var(--warn)"}>
                {conc.n_concordant}/{conc.n} concordant ({num(conc.concordance)})
              </Pill>
              <span className="text-[11px] text-fg-faint">{conc.standard} (DOI {conc.standard_doi})</span>
            </div>
            {conc.discordances?.length > 0 && (
              <ul className="space-y-1 text-xs text-fg-dim">
                {conc.discordances.map((d, i) => (
                  <li key={i}><code>{d.name}</code>: expected {d.label}, Guardian → {d.guardian_decision} ({d.common_mechanism_status})</li>
                ))}
              </ul>
            )}
            <p className="text-[11px] leading-relaxed text-fg-faint">{conc.note}</p>
          </div>
        )}
      </Card>
    </div>
  );
}
