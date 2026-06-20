// Scope & About, the honesty contract, made browsable. The known-unknowns (what PEN-STACK refuses to answer),
// the oracle scope cards (what each model is and is NOT valid for), and the capability manifest (every tool,
// every one fabricates=False). This is the page that makes depending on PEN-STACK safe.
import React, { useEffect, useState } from "react";
import { api } from "../api.js";
import { Card, Spinner, ErrorNote, Pill, Stat } from "../components/ui.jsx";
import ProvenanceChip from "../components/ProvenanceChip.jsx";
import { titleCase } from "../lib/format.js";

export default function Scope() {
  const [scope, setScope] = useState(null);
  const [caps, setCaps] = useState(null);
  const [busy, setBusy] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    (async => {
      try {
        const [s, c] = await Promise.all([api.scope(), api.capabilities()]);
        setScope(s); setCaps(c);
      } catch (e) { setError(e); } finally { setBusy(false); }
    })();
  }, []);

  if (busy) return <Card><Spinner label="Loading the honesty contract…" /></Card>;
  if (error) return <Card title="Scope"><ErrorNote error={error} /></Card>;

  return (
    <div className="space-y-4">
      <Card title="The honesty contract" subtitle="Decision-support, not a clinical directive. Every number is tool-sourced; what can't be computed is listed, never guessed.">
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <Stat label="Tools" value={caps?.tools?.length} />
          <Stat label="All fabricate?" value={caps?.tools?.every((t) => t.fabricates === false) ? "none" : "some"} color="var(--ok)" />
          <Stat label="Known-unknowns" value={scope?.known_unknowns?.length} color="var(--warn)" />
          <Stat label="Scope cards" value={scope?.oracle_scope_cards?.length} />
        </div>
      </Card>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card title="What PEN-STACK refuses to answer" subtitle="The known-unknowns registry, the boundary the engine will not cross.">
          <ul className="space-y-2">
            {(scope?.known_unknowns || []).map((k) => (
              <li key={k.id} className="rounded-lg border border-warn/25 bg-warn/5 p-3">
                <div className="text-sm font-medium text-fg">{k.title}</div>
                {k.requires && <div className="mt-0.5 text-[11px] text-fg-dim">requires: {k.requires}</div>}
                {k.why && <div className="mt-0.5 text-[11px] text-fg-faint">{k.why}</div>}
              </li>
            ))}
          </ul>
        </Card>

        <Card title="Oracle scope cards" subtitle="Each model states what it IS and IS NOT valid for; cross those and the output is flagged, never asserted.">
          <ul className="space-y-2">
            {(scope?.oracle_scope_cards || []).map((c, i) => (
              <li key={i} className="rounded-lg border border-line bg-ink-900 p-3">
                <div className="flex items-center justify-between gap-2">
                  <span className="text-sm font-medium">{c.model || c.family}</span>
                  <div className="flex items-center gap-1.5">
                    {c.version && <Pill>{c.version}</Pill>}
                    {c.output_kind && <Pill color="var(--brand)">{c.output_kind}</Pill>}
                  </div>
                </div>
                {c.valid_for && <div className="mt-1 text-[11px] text-ok">valid for: {arr(c.valid_for)}</div>}
                {c.not_valid_for && <div className="mt-0.5 text-[11px] text-warn">not valid for: {arr(c.not_valid_for)}</div>}
              </li>
            ))}
          </ul>
        </Card>
      </div>

      <Card title="Capability manifest" subtitle="The self-describing contract an external agent routes on, every tool, none fabricates.">
        <div className="grid gap-2 sm:grid-cols-2">
          {(caps?.tools || []).map((t) => (
            <div key={t.name} className="rounded-lg border border-line bg-ink-900 p-3">
              <div className="flex items-center justify-between">
                <span className="font-mono text-xs text-fg">{t.name}</span>
                <Pill color={t.fabricates === false ? "var(--ok)" : "var(--bad)"}>
                  fabricates: {String(t.fabricates)}
                </Pill>
              </div>
              {t.summary && <p className="mt-1 text-[11px] text-fg-dim">{t.summary}</p>}
            </div>
          ))}
        </div>
        {scope?.policy && (
          <p className="mt-3 rounded-lg border border-line bg-ink-900 p-3 text-[11px] leading-relaxed text-fg-dim">
            <strong className="text-fg">Policy.</strong> {typeof scope.policy === "string" ? scope.policy : JSON.stringify(scope.policy)}
          </p>
        )}
      </Card>
    </div>
  );
}

const arr = (x) => (Array.isArray(x) ? x.join(", ") : String(x));
