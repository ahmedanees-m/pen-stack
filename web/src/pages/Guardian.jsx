// Guardian, the biosecurity / dual-use screen. clear / flag / escalate / refuse, with the reason and an audit
// note. This is the orthogonal safety axis: a refused design is never scored on efficacy.
import React, { useState } from "react";
import { api } from "../api.js";
import { Card, Button, Spinner, ErrorNote, Pill } from "../components/ui.jsx";
import DesignForm, { DEFAULT_DESIGN } from "../components/DesignForm.jsx";
import SafetyBadge from "../components/SafetyBadge.jsx";

const PRESETS = [
  { label: "Benign, human Factor IX", patch: { cargo_function: "human factor IX", pfam_domains: [] } },
  { label: "Hazard, ricin-like RIP", patch: { cargo_function: "ricin-like ribosome-inactivating protein", pfam_domains: ["PF00161"] } },
  { label: "Dual-use, toxin domain", patch: { cargo_function: "cholera-like enterotoxin subunit", pfam_domains: ["PF01375"] } },
];

export default function Guardian() {
  const [design, setDesign] = useState({ ...DEFAULT_DESIGN, actor: "web" });
  const [res, setRes] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);

  async function run(d = design) {
    setBusy(true); setError(null);
    try { setRes(await api.safety(d)); } catch (e) { setError(e); setRes(null); } finally { setBusy(false); }
  }

  return (
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
                    </div>
                  </li>
                ))}
              </ul>
            )}
            {res.provenance?.registry_version && (
              <p className="text-[11px] text-fg-faint">Registry: <span className="font-mono">{res.provenance.registry_version}</span></p>
            )}
          </div>
        )}
      </Card>
    </div>
  );
}
