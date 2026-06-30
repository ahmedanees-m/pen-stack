// ImmuneProfileCard, the per-axis immune-risk profile (genotox / CD8 / innate / NAb / anti-PEG). NEVER a single
// fused number: the engine sets collapsed_score=None on purpose, and this card honours that, each axis renders
// its own value, uncertainty band, validation label, and provenance. A fused score would overstate certainty.
import React from "react";
import ConfidenceBand from "./ConfidenceBand.jsx";
import ProvenanceChip from "./ProvenanceChip.jsx";
import { num, statusOf, titleCase } from "../lib/format.js";

// hideWriterAxes (default true): the writer-as-antigen axes (MHC-II / ADA over the writer enzyme) now live on the
// Writer Atlas page (v7.1.8), where the writer is chosen, so this delivery-immunity card shows only the vehicle/
// cargo axes (genotox / CD8 / innate / NAb / anti-PEG). The engine still returns the writer axes for API callers.
const _WRITER_AXES = new Set(["mhc2_writer", "ada_writer"]);

export default function ImmuneProfileCard({ profile, hideWriterAxes = true }) {
  if (!profile) return null;
  const axes = profile.axes || {};
  const names = Object.keys(axes).filter((n) => !(hideWriterAxes && _WRITER_AXES.has(n)));

  return (
    <div>
      <div className="mb-3 flex flex-wrap items-center gap-2">
        <span className="text-sm font-semibold text-fg">Immune-risk profile</span>
        <span className="chip" style={{ color: "var(--warn)", borderColor: "var(--warn)55" }}>
          per-axis · never collapsed
        </span>
        {profile.route_modifier?.route && <span className="chip">route: {profile.route_modifier.route}</span>}
        {profile.administration_modifier && (
          <span className="chip"
                style={profile.administration_modifier.context === "ex_vivo" ? { color: "var(--warn)", borderColor: "var(--warn)55" } : undefined}>
            {profile.administration_modifier.context.replace("_", " ")}
          </span>
        )}
      </div>

      <div className="grid gap-2.5 sm:grid-cols-2">
        {names.map((name) => {
          const a = axes[name] || {};
          const v = a.value;
          const unc = a.uncertainty ?? 0;
          const st = statusOf(a);
          const available = a.available !== false && v !== null && v !== undefined;
          return (
            <div key={name} className="rounded-lg border border-line bg-ink-900 p-3">
              <div className="mb-1.5 flex items-center justify-between gap-2">
                <span className="text-xs font-semibold text-fg">{titleCase(name)}</span>
                <span className="text-[11px] tabular-nums text-fg-dim">
                  {available ? `${num(v)}${unc ? ` ± ${num(unc)}` : ""}` : "n/a"}
                </span>
              </div>
              <ConfidenceBand
                lo={available ? Math.max(0, v - unc) : null}
                hi={available ? Math.min(1, v + unc) : null}
                point={available ? v : null}
                status={available ? st : "out_of_scope"}
                label={name}
              />
              {/* self-explanatory: what THIS value means, in plain words (engine-provided), not just the number */}
              <p className="mt-2 text-[11px] leading-snug text-fg-dim">
                {a.meaning || a.validation || a.note || ""}
              </p>
              {/* administration (in-vivo/ex-vivo) muting: explain why this vector-facing axis was muted ex vivo */}
              {a.administration_muted && (
                <p className="mt-1.5 rounded border border-warn/30 bg-warn/5 px-2 py-1 text-[10px] leading-snug"
                   style={{ color: "var(--warn)" }}>
                  ex-vivo muted{a.pre_admin_value != null ? ` · in-vivo value was ${num(a.pre_admin_value)}` : ""}: {a.note}
                </p>
              )}
              <div className="mt-1 flex items-center justify-between gap-2">
                <span className="text-[10px] leading-tight text-fg-faint">
                  {a.guide?.computed ? `Computed: ${a.guide.computed}` : ""}
                </span>
                {a.scope_card && <ProvenanceChip source={a.scope_card} />}
              </div>
            </div>
          );
        })}
      </div>

      {/* writer-as-antigen: which writer enzyme drove the MHC-II/ADA axes, and whether it is the dominant antigen.
          Hidden here when the writer axes live on the Writer Atlas (v7.1.8); shown for API callers that pass a writer. */}
      {!hideWriterAxes && profile.writer_as_antigen && (
        <div className="mt-3 rounded-lg border border-line bg-ink-900 p-3 text-[11px] leading-snug">
          <div className="flex flex-wrap items-center gap-2">
            <span className="font-semibold text-fg">Writer as antigen</span>
            <span className="chip">{profile.writer_as_antigen.representative || profile.writer_as_antigen.writer_family}</span>
            {profile.writer_as_antigen.is_foreign != null && (
              <span className="chip" style={{ color: profile.writer_as_antigen.is_foreign ? "var(--warn)" : "var(--ok)" }}>
                {profile.writer_as_antigen.is_foreign ? "foreign" : "self"}
              </span>
            )}
            {profile.writer_as_antigen.dominant_antigen && (
              <span className="chip" style={profile.writer_as_antigen.writer_dominant_risk ? { color: "var(--warn)", borderColor: "var(--warn)55" } : undefined}>
                dominant antigen: {profile.writer_as_antigen.dominant_antigen}
              </span>
            )}
          </div>
          <p className="mt-1.5 text-fg-dim">{profile.writer_as_antigen.note}</p>
        </div>
      )}

      {/* administration context: explain the in-vivo / ex-vivo modifier on the vector-facing axes */}
      {profile.administration_modifier && (
        <p className="mt-3 text-[11px] leading-snug text-fg-faint">
          <span style={{ color: profile.administration_modifier.context === "ex_vivo" ? "var(--warn)" : "var(--ok)" }}>
            {profile.administration_modifier.context.replace("_", " ")}
          </span>{" "}
          — {profile.administration_modifier.effect}
        </p>
      )}

      {/* legend: explain the overloaded "extrapolating" badge in plain words, once, under the grid */}
      <p className="mt-3 text-[11px] leading-snug text-fg-faint">
        <span style={{ color: "var(--warn)" }}> extrapolating</span> means the axis is a{" "}
        <span className="text-fg-dim">proxy</span>, a mechanistic or population estimate, <em>not</em> validated
        against a measured clinical outcome. Read those values as directional, not guaranteed. Scale is 0-1, higher
        is safer.
      </p>

      {profile.collapsed_score === null && (
        <p className="mt-2 text-[11px] text-fg-faint">
          No single fused immune score is asserted (<span className="font-mono">collapsed_score = None</span>),
          the axes measure different mechanisms on different evidence; averaging them would manufacture certainty.
        </p>
      )}
    </div>
  );
}
