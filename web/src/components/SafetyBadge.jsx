// SafetyBadge — the Guardian's decision: clear / flag / escalate / refuse. A refused design is NOT evaluated
// further (the engine stops); the badge makes that visible and shows the reason.
import React from "react";
import { SAFETY_COLOR, titleCase } from "../lib/format.js";

const ICON = {
  clear: "M20 6 9 17l-5-5",
  flag: "M12 9v4m0 4h.01M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0Z",
  escalate: "M12 9v4m0 4h.01M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0Z",
  refuse: "M18 6 6 18M6 6l12 12",
};

export default function SafetyBadge({ decision, reason, compact = false }) {
  if (!decision) return null;
  const color = SAFETY_COLOR[decision] || "var(--muted)";
  return (
    <div className={compact ? "inline-flex items-center gap-2" : "flex items-start gap-3 rounded-lg border px-3 py-2"}
         style={compact ? undefined : { borderColor: color + "55", background: color + "12" }}>
      <span className="inline-flex h-6 w-6 shrink-0 items-center justify-center rounded-full"
            style={{ background: color + "22", color }}>
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
          <path d={ICON[decision] || ICON.flag} stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </span>
      <div>
        <div className="text-sm font-semibold" style={{ color }}>{titleCase(decision)}</div>
        {!compact && reason && <div className="text-xs text-fg-dim">{reason}</div>}
      </div>
    </div>
  );
}
