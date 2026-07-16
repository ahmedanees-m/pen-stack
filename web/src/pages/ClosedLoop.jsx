// Closed Loop (v7.0): the design->build->test->learn features that were previously API-only (a tester
// flagged they had no UI). Three surfaces, all safety-first and explicit about the mock/dry-run boundary:
//   * Cloud-lab submission (/api/cloudlab), verify runs FIRST; a cleared design returns a DRAFT protocol + a
//     mock/dry-run job receipt, a flagged design is refused with NO protocol emitted.
//   * SDL-brain benchmark (/api/brains), the EIG/VOI designer vs random/greedy on a shared task, BayBE/Atlas
//     cited (no live BayBE runs unless installed).
//   * World-model graph (/api/graph/query), multi-hop writer -> locus -> vehicle, each path provenanced.
import React, { useState } from "react";
import WhatYouGet from "../components/WhatYouGet.jsx";
import { api } from "../api.js";
import { Card, Button, Spinner, ErrorNote, Field, Select, Pill } from "../components/ui.jsx";
import DesignForm, { DEFAULT_DESIGN } from "../components/DesignForm.jsx";
import { num } from "../lib/format.js";

const PROVIDERS = ["mock", "ginkgo", "emerald", "strateos"];
const CARGO_FORMS = [{ value: "", label: "any" }, { value: "DNA", label: "DNA" }, { value: "RNA", label: "RNA" }, { value: "mRNA", label: "mRNA" }];

// ---- Cloud-lab submission (safety-gated protocol export) -------------------------------------------------
function CloudLabCard() {
  const [design, setDesign] = useState({ ...DEFAULT_DESIGN });
  const [provider, setProvider] = useState("mock");
  const [res, setRes] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);

  async function submit() {
    setBusy(true); setError(null); setRes(null);
    try { setRes(await api.cloudlab({ design, provider })); }
    catch (e) { setError(e); } finally { setBusy(false); }
  }

  const blocked = res && res.blocked;
  return (
    <Card title="Build & submit (cloud-lab)" subtitle="Verify runs FIRST, a cleared design gets a DRAFT protocol + mock/dry-run receipt; a hazardous one is refused with no protocol.">
      <DesignForm design={design} onChange={setDesign} showCargoSeq={false} />
      <div className="mt-3 grid grid-cols-2 gap-3">
        <Field label="Provider" hint="only 'mock' is wired (local dry-run); the named labs route to the mock path, a real run needs a partner">
          <Select value={provider} onChange={setProvider} options={PROVIDERS} />
        </Field>
      </div>
      <p className="mt-2 text-[11px] text-fg-faint">Tip: set Cargo function to a hazard (e.g. <code>ricin-like RIP</code>) to see the biosecurity gate refuse before any protocol is emitted.</p>
      <div className="mt-4"><Button onClick={submit} disabled={busy}>Safety-gate & submit</Button></div>
      {busy ? <div className="mt-3"><Spinner label="Verifying & exporting…" /></div> : error ? <div className="mt-3"><ErrorNote error={error} /></div> : res && (
        <div className="mt-3 space-y-2 text-sm">
          {blocked ? (
            <>
              <div className="flex flex-wrap items-center gap-2">
                <Pill color="var(--bad)">refused · no protocol emitted</Pill>
                <Pill>human in control</Pill>
              </div>
              <p className="text-fg-dim">{res.reason}</p>
              <p className="text-[11px] text-fg-faint">{res.note}</p>
            </>
          ) : (
            <>
              <div className="flex flex-wrap items-center gap-2">
                <Pill color="var(--ok)">{res.status}</Pill>
                {res.dry_run && <Pill color="var(--warn)">dry-run</Pill>}
                <Pill>Level {res.autonomy_level} · human in control</Pill>
              </div>
              <div className="grid grid-cols-2 gap-2 text-[12px]">
                <div><span className="text-fg-faint">job id</span><div className="font-mono">{res.job_id}</div></div>
                <div><span className="text-fg-faint">biosecurity gate</span><div>{res.biosecurity_gate}</div></div>
              </div>
              <div>
                <div className="mb-1 text-[11px] uppercase tracking-wide text-fg-faint">Protocol preview (DRAFT)</div>
                <pre className="max-h-40 overflow-auto rounded-lg border border-line bg-ink-950 p-2 text-[10.5px] leading-snug text-fg-dim whitespace-pre-wrap">{res.protocol_preview}</pre>
              </div>
              <p className="text-[11px] text-amber-300/80">{res.note}</p>
            </>
          )}
        </div>
      )}
    </Card>
  );
}

// ---- SDL-brain benchmark ---------------------------------------------------------------------------------
function BrainsCard() {
  const [res, setRes] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  async function run() {
    setBusy(true); setError(null);
    try { setRes(await api.brains()); } catch (e) { setError(e); } finally { setBusy(false); }
  }
  const g = res?.eig_vs_random;
  return (
    <Card title="SDL-brain benchmark" subtitle="The EIG/VOI experiment designer vs random / greedy on a shared retrospective task, reported verbatim, win or not.">
      <div><Button onClick={run} disabled={busy}>Run benchmark</Button></div>
      {busy ? <div className="mt-3"><Spinner label="Running acquisition benchmark…" /></div> : error ? <div className="mt-3"><ErrorNote error={error} /></div> : res && (
        <div className="mt-3 space-y-2 text-sm">
          <div className="flex flex-wrap items-center gap-2">
            <Pill color={g?.active_beats_random ? "var(--ok)" : "var(--warn)"}>
              active {g?.active_beats_random ? "beats" : "does not beat"} random
            </Pill>
            <span className="text-[12px] text-fg-dim">curve-area gap {num(g?.mean_gap, 3)} · CI [{num(g?.ci?.[0], 3)}, {num(g?.ci?.[1], 3)}]</span>
          </div>
          <p className="text-[12px] text-fg-dim">{res.result}</p>
          {res.baybe_installed === false && (
            <p className="rounded-lg border border-warn/25 bg-warn/5 px-3 py-2 text-[11px] leading-relaxed text-amber-300/80">
              <b>BayBE not installed in this deployment</b>, the head-to-head is the self-contained EIG-vs-random/greedy
              contrast; BayBE / Atlas are cited references, not an executed comparison here.
            </p>
          )}
          {res.references && (
            <ul className="space-y-1 text-[11px] text-fg-faint">
              {Object.entries(res.references).map(([k, v]) => <li key={k}><b className="text-fg-dim">{k}:</b> {v}</li>)}
            </ul>
          )}
          <p className="text-[11px] text-fg-faint">{res.note}</p>
        </div>
      )}
    </Card>
  );
}

// ---- World-model graph -----------------------------------------------------------------------------------
function GraphCard() {
  const [locus, setLocus] = useState("AAVS1");
  const [cargoForm, setCargoForm] = useState("");
  const [res, setRes] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  async function run() {
    if (!locus.trim()) return;
    setBusy(true); setError(null);
    try { setRes(await api.graphQuery(locus.trim(), cargoForm)); } catch (e) { setError(e); setRes(null); } finally { setBusy(false); }
  }
  return (
    <Card title="World-model graph" subtitle="Which writers reach a locus AND are deliverable, a multi-hop query, every path provenanced (no auto-edit).">
      <div className="grid grid-cols-2 gap-3">
        <Field label="Locus / gene"><input className="input" autoComplete="off" value={locus} onChange={(e) => setLocus(e.target.value)} placeholder="e.g. AAVS1" /></Field>
        <Field label="Cargo form filter"><Select value={cargoForm} onChange={setCargoForm} options={CARGO_FORMS} /></Field>
      </div>
      <div className="mt-4"><Button onClick={run} disabled={busy}>Query graph</Button></div>
      {busy ? <div className="mt-3"><Spinner label="Traversing the world model…" /></div> : error ? <div className="mt-3"><ErrorNote error={error} /></div> : res && (
        <div className="mt-3 space-y-2 text-sm">
          <div className="flex flex-wrap items-center gap-2">
            {res.resolved_locus && res.resolved_locus.toLowerCase() !== String(res.locus).trim().toLowerCase() && (
              <Pill>resolved to {res.resolved_locus}</Pill>
            )}
            {res.n_answers > 0 && (res.is_curated_safe_harbour
              ? <Pill color="var(--ok)">curated safe harbour</Pill>
              : <Pill color="var(--warn)">tier-1 candidate reach · not a curated safe harbour</Pill>)}
          </div>
          <p className="text-[12px] text-fg-dim">{res.n_answers} writer{res.n_answers === 1 ? "" : "s"} reach <code>{res.resolved_locus || res.locus}</code>{res.cargo_form ? ` deliverable as ${res.cargo_form}` : ""}.</p>
          {res.n_answers === 0 && <p className="text-[11px] text-fg-faint">{res.note}</p>}
          <ul className="space-y-2">
            {(res.answers || []).map((a, i) => (
              <li key={i} className="rounded-lg border border-line bg-ink-900 p-3">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="text-sm font-medium">{String(a.writer).replace(/_/g, " ")}</span>
                  <Pill>{a.output_form}</Pill>
                  <span className="text-[11px] text-fg-faint">{(a.vehicles || []).length} vehicle(s)</span>
                </div>
                <div className="mt-1.5 text-[11px] text-fg-faint">{(a.vehicles || []).map((v) => v.replace(/_/g, " ")).join(" · ")}</div>
                {(a.provenance_path || []).length > 0 && (
                  <ul className="mt-1.5 space-y-0.5 text-[10.5px] text-fg-faint">
                    {a.provenance_path.map((p, j) => (
                      <li key={j}><code>{p.etype}</code>, {p.evidence}{p.provenance?.source ? ` · ${p.provenance.source}` : ""}</li>
                    ))}
                  </ul>
                )}
              </li>
            ))}
          </ul>
        </div>
      )}
    </Card>
  );
}

export default function ClosedLoop() {
  return (
    <div className="space-y-4">
      <WhatYouGet
        intro="The closed loop (design → build → test → learn), Level 3 with a human in control. These closed-loop capabilities were previously reachable only via the API, here they are, safety-first and explicit about the mock/dry-run boundary."
        features={[
          { name: "Build & submit", tells: "would a cloud lab accept this design?", output: "verify-first → DRAFT protocol + mock/dry-run receipt, or a refusal" },
          { name: "SDL-brain benchmark", tells: "does the EIG/VOI designer beat random?", output: "curve-area gap + CI, BayBE / Atlas cited (falsifiable)" },
          { name: "World-model graph", tells: "which writers reach a locus AND are deliverable", output: "provenanced multi-hop paths" },
        ]}
        example="A Factor IX cassette at AAVS1 → verify passes → a DRAFT Opentrons protocol + a mock job receipt (no wet run). A ricin cargo → refused before any protocol is emitted."
      />
      <div className="grid gap-4 lg:grid-cols-2">
        <CloudLabCard />
        <div className="space-y-4">
          <BrainsCard />
          <GraphCard />
        </div>
      </div>
    </div>
  );
}
