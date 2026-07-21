// A plain "What this page gives you" panel: a simple list of the outputs you can get here + one worked example.
// Additive to the per-page "How to read these scores" (ScoreGuide): this one answers "what is this page FOR and
// what can I get from it", that one answers "what do the numbers mean". Pure presentation.
import React, { useState } from "react";
import { Icon } from "./icons.jsx";

export default function WhatYouGet({ intro, features = [], example, defaultOpen = true }) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="rounded-xl border border-brand/25 bg-brand/5">
      <button onClick={() => setOpen((o) => !o)}
              className="flex w-full items-center gap-2 rounded-xl px-4 py-2.5 text-left hover:bg-brand/10">
        <span className="grid h-6 w-6 place-items-center rounded-md bg-brand/15 text-brand"><Icon name="spark" size={14} /></span>
        <span className="text-sm font-medium text-fg">What this page gives you</span>
        <span className="ml-2 text-[11px] text-fg-faint">{open ? "hide" : "the outputs + an example"}</span>
        <Icon name="arrow" size={14} className={`ml-auto text-fg-faint transition-transform ${open ? "rotate-90" : ""}`} />
      </button>
      {open && (
        <div className="space-y-3 border-t border-brand/20 px-4 py-3.5">
          {intro && <p className="text-sm leading-relaxed text-fg-dim">{intro}</p>}
          {features.length > 0 && (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-line text-left text-[11px] uppercase tracking-wide text-fg-faint">
                    <th className="py-1.5 pr-3">You can get</th><th className="py-1.5 pr-3">What it tells you</th><th className="py-1.5">Output</th>
                  </tr>
                </thead>
                <tbody>
                  {features.map((f, i) => (
                    <tr key={i} className="border-b border-line/40 align-top">
                      <td className="py-1.5 pr-3 font-medium text-fg">{f.name}</td>
                      <td className="py-1.5 pr-3 text-fg-dim">{f.tells}</td>
                      <td className="py-1.5 text-[12px] text-fg-faint">{f.output}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          {example && (
            <p className="rounded-lg border border-line bg-ink-900 px-3 py-2 text-[12px] leading-relaxed text-fg-dim">
              <span className="font-semibold text-fg">Example, </span>{example}
            </p>
          )}
        </div>
      )}
    </div>
  );
}
