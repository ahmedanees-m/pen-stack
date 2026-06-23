// Delivery & Immunity, the per-axis immune-risk profile explorer. Five axes, a route modifier, and the
// known-unknowns. The whole point: there is no single immune number; this page refuses to invent one.
import React, { useState } from "react";
import ScoreGuide from "../components/ScoreGuide.jsx";
import { api } from "../api.js";
import { Card, Button, Spinner, ErrorNote } from "../components/ui.jsx";
import DesignForm, { DEFAULT_DESIGN, VEHICLES } from "../components/DesignForm.jsx";
import ImmuneProfileCard from "../components/ImmuneProfileCard.jsx";
import ScopeLedger from "../components/ScopeLedger.jsx";

export default function Delivery() {
  const [design, setDesign] = useState(DEFAULT_DESIGN);
  const [res, setRes] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);

  async function run(d = design) {
    setBusy(true); setError(null);
    try { setRes(await api.immune(d)); } catch (e) { setError(e); setRes(null); } finally { setBusy(false); }
  }

  return (
    <div className="space-y-4">
      <ScoreGuide
        intro="Immune risk is reported as FIVE separate axes (0–1, higher = lower risk), never collapsed into one number. Each is a mechanistic or population proxy, not a patient-specific prediction."
        items={[
          { term: "Genotoxicity", scale: "higher = safer", meaning: "1.0 = episomal / non-integrating (no insertional-oncogenesis mechanism); lower = an integrating vector enriched for integrations near oncogenes." },
          { term: "CD8 epitope", scale: "higher = less visible", meaning: "1 − fraction of the capsid presentable to cytotoxic T cells across a frequent HLA-I panel (MHCflurry). Sequence-intrinsic, CD8/MHC-I only." },
          { term: "Innate / NAb / anti-PEG", scale: "higher = lower barrier", meaning: "Innate-sensing load (CpG/dsRNA), pre-existing neutralizing-antibody eligibility (serosurveys), and anti-PEG barrier (PEG vehicles only)." },
          { term: "Capsid fitness", scale: "0–1 candidate", meaning: "A learned AAV packaging-viability score (FLIP-AAV-trained). A candidate for the measured packaging axis, not an in-vivo tropism claim." },
        ]}
        caveats={[
          "Patient-specific immune MAGNITUDE (titer, realized response) is a known-unknown — never predicted.",
          "In-vivo human tropism of a novel capsid abstains; only approved-serotype tissue priors are given.",
        ]} />

      <Card title="Vehicle & context" subtitle="Switch the vehicle to watch the axes move, the engine recomputes each.">
        <div className="mb-3 flex flex-wrap gap-1.5">
          {VEHICLES.map((v) => (
            <button key={v} onClick={() => { const d = { ...design, delivery_vehicle: v }; setDesign(d); run(d); }}
              className={`rounded-lg border px-2.5 py-1 text-xs ${design.delivery_vehicle === v ? "border-brand/50 bg-brand/15 text-brand" : "border-line bg-ink-900 text-fg-dim hover:text-fg"}`}>
              {v.replace(/_/g, " ")}
            </button>
          ))}
        </div>
        <DesignForm design={design} onChange={setDesign} />
        <div className="mt-4"><Button onClick={() => run()} disabled={busy}>Profile immune risk</Button></div>
      </Card>

      <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_320px]">
        <Card title="Immune-risk profile">
          {busy ? <Spinner /> : error ? <ErrorNote error={error} /> : !res ? (
            <p className="text-sm text-fg-faint">Profile a design to see the five axes.</p>
          ) : <ImmuneProfileCard profile={res} />}
        </Card>
        <div>
          {res && <ScopeLedger knownUnknowns={res.known_unknowns} />}
          {res?.note && <p className="mt-3 text-[11px] text-fg-faint">{res.note}</p>}
        </div>
      </div>
    </div>
  );
}
