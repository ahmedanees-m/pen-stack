// A collapsible "How to read these scores" panel. Used across every tool page so a number like 0.92 is never
// shown without an explanation of its scale, what it means, and how to use it. Pure presentation.
import React, { useState } from "react";
import { Icon } from "./icons.jsx";

export default function ScoreGuide({ title = "How to read these scores", intro, items = [], caveats = [], defaultOpen = false }) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="rounded-xl border border-line bg-ink-900/40">
      <button onClick={() => setOpen((o) => !o)} className="flex w-full items-center gap-2 rounded-xl px-4 py-2.5 text-left hover:bg-ink-800/40">
        <span className="grid h-6 w-6 place-items-center rounded-md bg-brand/10 text-brand"><Icon name="scope" size={14} /></span>
        <span className="text-sm font-medium text-fg">{title}</span>
        <span className="ml-2 text-[11px] text-fg-faint">{open ? "hide" : "what the numbers mean"}</span>
        <Icon name="arrow" size={14} className={`ml-auto text-fg-faint transition-transform ${open ? "rotate-90" : ""}`} />
      </button>
      {open && (
        <div className="space-y-3 border-t border-line px-4 py-3.5 text-sm">
          {intro && <p className="leading-relaxed text-fg-dim">{intro}</p>}
          {items.length > 0 && (
            <dl className="space-y-2.5">
              {items.map((it, i) => (
                <div key={i} className="grid gap-0.5 sm:grid-cols-[150px_1fr] sm:gap-4">
                  <dt className="font-medium text-fg">
                    {it.term}
                    {it.scale && <span className="ml-1.5 text-[11px] font-normal text-fg-faint">{it.scale}</span>}
                  </dt>
                  <dd className="leading-relaxed text-fg-dim">{it.meaning}</dd>
                </div>
              ))}
            </dl>
          )}
          {caveats.length > 0 && (
            <ul className="space-y-1.5 border-t border-line pt-2.5 text-xs text-fg-faint">
              {caveats.map((c, i) => (
                <li key={i} className="flex gap-1.5"><span className="mt-px text-warn">▲</span><span>{c}</span></li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}
