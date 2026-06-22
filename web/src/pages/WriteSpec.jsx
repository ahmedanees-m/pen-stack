// Describe your write: turn a plain-language genome-writing goal into a typed, ontology-backed WriteSpec.
// Every field shows its provenance (explicit / inferred / user / unresolved); inferred fields list their
// assumption; anything underspecified raises a clarifying question rather than a guess; and the feasibility
// verdict (reachability + deliverability + legality) names any blocking constraint. A WriteSpec is a request,
// not a claim: the extractor never fabricates intent.
import React, { useState } from "react";
import { api } from "../api.js";
import { Card, Button, Spinner, ErrorNote, Field } from "../components/ui.jsx";

const PROV_COLOR = { explicit: "var(--ok)", inferred: "var(--warn)", user: "var(--brand, #6ea8fe)", unresolved: "var(--bad)" };
const EXAMPLE = "Insert a 3 kb GFP cassette with a promoter and polyA at AAVS1 in HEK293T, scarless, with a doxycycline-inducible safety switch";

function Chip({ label, prov }) {
  const c = PROV_COLOR[prov] || "var(--muted)";
  return (
    <span className="inline-flex items-center gap-1 rounded border px-2 py-0.5 text-xs" style={{ borderColor: c }}>
      {label}<span style={{ color: c }} className="uppercase text-[10px]">{prov}</span>
    </span>
  );
}

function Resolved({ r }) {
  if (!r) return <span className="text-fg-faint">n/a</span>;
  return (
    <span className="font-mono text-xs">
      {r.label || r.text} {r.id && <span className="text-fg-faint">[{r.id}{r.ontology ? ` · ${r.ontology}` : ""}]</span>}
    </span>
  );
}

export default function WriteSpec() {
  const [prose, setProse] = useState(EXAMPLE);
  const [res, setRes] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);

  async function run() {
    setBusy(true); setError(null); setRes(null);
    try { setRes(await api.writespec(prose)); } catch (e) { setError(e); } finally { setBusy(false); }
  }

  const ws = res?.writespec;
  const prov = ws?.provenance || {};
  const feas = res?.feasibility;

  return (
    <div className="space-y-4">
      <Card title="Describe your write" subtitle="Plain language in; a typed, ontology-backed WriteSpec out. Inferred fields are labelled, ambiguous ones are asked, unresolved stays null.">
        <Field label="Your genome-writing goal">
          <textarea className="input text-sm h-24" value={prose} onChange={(e) => setProse(e.target.value)} />
        </Field>
        <div className="mt-3"><Button onClick={run} disabled={busy}>Parse to WriteSpec</Button></div>
      </Card>

      {busy && <Card><Spinner label="Parsing to a typed WriteSpec…" /></Card>}
      {error && <Card><ErrorNote error={error} /></Card>}

      {ws && (
        <Card title="WriteSpec" subtitle={`A request, not a claim · ${res.actionable ? "actionable" : "needs clarification"}`}>
          <dl className="grid gap-2 text-sm sm:grid-cols-2">
            <div><dt className="text-fg-faint text-xs">Write type</dt><dd><Chip label={ws.write_type} prov={prov.write_type || "explicit"} /></dd></div>
            <div><dt className="text-fg-faint text-xs">Target ({ws.target?.kind})</dt><dd>
              {ws.target?.gene && <Resolved r={ws.target.gene} />}
              {ws.target?.phenotype && <> <span className="text-fg-faint">goal:</span> <Resolved r={ws.target.phenotype} /></>}
              {ws.target?.att_site && <span className="font-mono text-xs">{ws.target.att_site}</span>}
              {ws.target?.kind === "unspecified" && <span className="text-fg-faint">unspecified</span>}
            </dd></div>
            <div><dt className="text-fg-faint text-xs">Cell type</dt><dd><Resolved r={ws.cell_type} /></dd></div>
            <div><dt className="text-fg-faint text-xs">Cargo</dt><dd className="space-y-1">
              {(ws.cargo || []).length === 0 ? <span className="text-fg-faint">none specified</span> :
                ws.cargo.map((c, i) => <div key={i}><span className="text-xs">{c.name}</span> {c.role && <Resolved r={c.role} />} {c.length_bp ? <span className="text-fg-faint text-xs">{c.length_bp} bp</span> : null}</div>)}
            </dd></div>
          </dl>
          <div className="mt-3">
            <p className="text-fg-faint text-xs mb-1">Constraints</p>
            <div className="flex flex-wrap gap-2">
              {Object.entries(ws.constraints || {}).filter(([, v]) => v != null).map(([k, v]) => (
                <Chip key={k} label={`${k}=${v && v.id ? v.label : String(v)}`} prov={prov[`constraints.${k}`] || "explicit"} />
              ))}
            </div>
          </div>
          {ws.assumptions?.length > 0 && (
            <div className="mt-3"><p className="text-amber-300 text-xs mb-1">Assumptions (inferred fields, labelled)</p>
              <ul className="list-disc pl-5 text-xs text-fg-dim">{ws.assumptions.map((a, i) => <li key={i}>{a}</li>)}</ul></div>
          )}
        </Card>
      )}

      {res?.clarifications?.length > 0 && (
        <Card title="Clarifying questions" subtitle="Underspecified or ambiguous fields, asked rather than guessed">
          <ul className="list-disc pl-5 text-sm text-fg-dim space-y-1">{res.clarifications.map((q, i) => <li key={i}>{q}</li>)}</ul>
        </Card>
      )}

      {feas && (
        <Card title="Feasibility" subtitle="Necessary conditions only (reachability + deliverability + legality); not efficacy">
          <p className="text-sm mb-2">Verdict: {feas.feasible
            ? <strong style={{ color: "var(--ok)" }}>feasible</strong>
            : <strong style={{ color: "var(--bad)" }}>infeasible</strong>}</p>
          <ul className="space-y-1 text-xs">
            {Object.entries(feas.checks || {}).map(([k, c]) => (
              <li key={k}><span className="font-mono">{k}</span>: <span style={{ color: c.ok === true ? "var(--ok)" : c.ok === false ? "var(--bad)" : "var(--warn)" }}>{c.ok === true ? "ok" : c.ok === false ? "blocked" : "indeterminate"}</span> <span className="text-fg-faint">{c.status}</span></li>
            ))}
          </ul>
          {feas.repairs?.length > 0 && (
            <div className="mt-2"><p className="text-fg-faint text-xs">Repairs</p>
              <ul className="list-disc pl-5 text-xs text-fg-dim">{feas.repairs.map((r, i) => <li key={i}><b>{r.constraint}:</b> {typeof r.hint === "string" ? r.hint : JSON.stringify(r.hint)}</li>)}</ul></div>
          )}
        </Card>
      )}
    </div>
  );
}
