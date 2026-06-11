// ScopeLedger — "What I can't tell you." The known-unknowns for the current question: the honesty boundary the
// engine refuses to cross. It is present on EVERY answer (a small note when nothing is flagged, the list when
// something is). Accepts either the immune profile's known_unknowns (strings) or the /scope manifest entries.
import React from "react";
import { humanize } from "../lib/format.js";

export default function ScopeLedger({ knownUnknowns = [], outOfScope = null, dense = false }) {
  const items = (knownUnknowns || []).map((k) =>
    typeof k === "string" ? { id: k, title: humanize(k) } : k);
  const nothing = items.length === 0 && !outOfScope;

  return (
    <div className={`rounded-lg border border-line bg-ink-900/60 ${dense ? "p-3" : "p-4"}`}>
      <div className="mb-1.5 flex items-center gap-2">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" className="text-warn">
          <circle cx="12" cy="12" r="9" stroke="currentColor" strokeWidth="2" />
          <path d="M12 8h.01M11 12h1v4h1" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
        <h4 className="text-xs font-semibold uppercase tracking-wide text-fg-dim">What I can&apos;t tell you</h4>
      </div>
      {outOfScope && (
        <p className="mb-2 rounded-md border border-warn/30 bg-warn/10 px-2.5 py-1.5 text-xs text-warn">
          This question is <strong>out of scope</strong>: {outOfScope.title}. {outOfScope.why}
        </p>
      )}
      {nothing ? (
        <p className="text-xs text-fg-faint">Nothing flagged for this query — but PEN-STACK never predicts in-vivo
          response magnitude, patient-specific titer, or long-term clinical outcome.</p>
      ) : (
        <ul className="space-y-1">
          {items.map((k) => (
            <li key={k.id} className="flex gap-2 text-xs text-fg-dim">
              <span className="mt-1 h-1 w-1 shrink-0 rounded-full bg-warn" />
              <span><span className="text-fg">{k.title}</span>{k.requires ? <span className="text-fg-faint"> — requires {k.requires}</span> : null}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
