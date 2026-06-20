// ProvenanceChip, the dataset/model + version behind a number. Hover/focus reveals the scope card (what the
// source IS and IS NOT valid for). Provenance is not decoration: a number without a traceable source fails review.
import React, { useState } from "react";

export default function ProvenanceChip({ source, version, validValidFor, notValidFor, output_kind }) {
  const [open, setOpen] = useState(false);
  if (!source) return null;
  return (
    <span className="relative inline-block">
      <button
        type="button"
        className="chip hover:border-brand/40 hover:text-brand focus:outline-none focus:ring-1 focus:ring-brand/40"
        onMouseEnter={() => setOpen(true)}
        onMouseLeave={() => setOpen(false)}
        onFocus={() => setOpen(true)}
        onBlur={() => setOpen(false)}
        aria-label={`source: ${source}${version ? " " + version : ""}`}
      >
        <svg width="11" height="11" viewBox="0 0 24 24" fill="none" className="opacity-70">
          <path d="M12 2 3 7v10l9 5 9-5V7l-9-5Z" stroke="currentColor" strokeWidth="2" strokeLinejoin="round" />
        </svg>
        {source}{version ? ` · ${version}` : ""}
      </button>
      {open && (notValidFor || validValidFor) && (
        <span className="fade-in absolute left-0 top-full z-20 mt-1 w-64 rounded-lg border border-line bg-ink-800 p-2.5 text-[11px] leading-relaxed shadow-panel">
          {output_kind && <div className="mb-1 text-fg-dim">kind: <span className="font-mono">{output_kind}</span></div>}
          {validValidFor && <div className="text-ok">valid for: {arr(validValidFor)}</div>}
          {notValidFor && <div className="mt-0.5 text-warn">not valid for: {arr(notValidFor)}</div>}
        </span>
      )}
    </span>
  );
}

const arr = (x) => (Array.isArray(x) ? x.join(", ") : String(x));
