// ConfidenceBand, an interval [low,, ●,, high] coloured by honesty status, with an OOD chevron. The single
// rule the whole UI rests on: a number is NEVER shown without this band (or a ProvenanceChip). When the engine
// abstains (no interval / out of scope), the band says so rather than drawing a fake point.
import React from "react";
import { STATUS_COLOR } from "../lib/format.js";

export default function ConfidenceBand({ lo, hi, point, status = "grounded", label }) {
  const color = STATUS_COLOR[status] || STATUS_COLOR.grounded;
  const has = point !== null && point !== undefined && !Number.isNaN(point);
  const clamp = (v) => Math.max(0, Math.min(1, Number(v)));
  const l = lo ?? point, h = hi ?? point;

  if (status === "out_of_scope" || !has) {
    return (
      <div className="band" role="img" aria-label={`${label || "value"}: out of scope or not computed`}>
        <div className="band-track" />
        <span className="band-label" style={{ color: STATUS_COLOR.out_of_scope }}>
          {status === "out_of_scope" ? "out of scope, not predicted" : "abstained, no calibrated value"}
        </span>
      </div>
    );
  }

  const ariaText = `${label ? label + ": " : ""}${Number(point).toFixed(2)} in [${Number(l).toFixed(2)}, ${Number(h).toFixed(2)}], ${status}`;
  return (
    <div className="band" role="img" aria-label={ariaText}>
      <div className="band-track">
        <span className="band-fill" style={{ left: `${clamp(l) * 100}%`, right: `${(1 - clamp(h)) * 100}%`, background: color }} />
        <span className="band-point" style={{ left: `${clamp(point) * 100}%`, background: color }} />
      </div>
      <span className="band-label" style={{ color }}>
        {Number(point).toFixed(2)}
        {lo != null && hi != null && <span className="text-fg-faint"> · [{Number(l).toFixed(2)}, {Number(h).toFixed(2)}]</span>}
        {status === "extrapolating" && <span> extrapolating</span>}
      </span>
    </div>
  );
}
