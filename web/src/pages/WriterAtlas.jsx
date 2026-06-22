// Writer Atlas, compare genome writers across families: confidence, mechanism, cargo capacity, deliverability,
// human-cell activity, reachability tier. The "measured vs candidate" split is shown explicitly: Tier-2/3
// reachability is candidate and needs experimental validation.
import React, { useEffect, useMemo, useState } from "react";
import { api } from "../api.js";
import { Card, Spinner, ErrorNote, Pill, Stat } from "../components/ui.jsx";
import { titleCase } from "../lib/format.js";

export default function WriterAtlas() {
  const [coverage, setCoverage] = useState(null);
  const [rows, setRows] = useState(null);
  const [family, setFamily] = useState("");
  const [busy, setBusy] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    (async () => {
      setBusy(true); setError(null);
      try {
        const [cov, atlas] = await Promise.all([api.atlasCoverage(), api.atlas("", 300)]);
        setCoverage(cov); setRows(atlas.rows || []);
      } catch (e) { setError(e); } finally { setBusy(false); }
    })();
  }, []);

  const families = useMemo(() => Array.from(new Set((rows || []).map((r) => r.family))).sort(), [rows]);
  const shown = (rows || []).filter((r) => !family || r.family === family);

  const conf = (c) => c === "measured" ? "grounded" : "extrapolating";
  const confColor = { measured: "var(--ok)", inferred: "var(--warn)", candidate: "var(--muted)" };

  if (busy) return <Card><Spinner label="Loading the Writer Atlas…" /></Card>;
  if (error) return <Card title="Writer Atlas"><ErrorNote error={error} /></Card>;

  return (
    <div className="space-y-4">
      {coverage && (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <Stat label="Families" value={coverage.families} />
          <Stat label="Systems" value={coverage.systems} />
          <Stat label="Measured" value={(coverage.coverage || []).reduce((a, c) => a + (c.measured || 0), 0)} color="var(--ok)" />
          <Stat label="Filter" value={family ? titleCase(family) : "all"} />
        </div>
      )}

      <Card title="Compare writers" subtitle="Every row carries its confidence; candidate reachability needs lab validation."
            right={
              <select className="input max-w-[180px]" value={family} onChange={(e) => setFamily(e.target.value)}>
                <option value="">all families</option>
                {families.map((f) => <option key={f} value={f}>{f}</option>)}
              </select>
            }>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead><tr className="border-b border-line text-left text-[11px] uppercase tracking-wide text-fg-faint">
              <th className="py-2 pr-3">System</th><th className="py-2 pr-3">Family</th>
              <th className="py-2 pr-3">Confidence</th><th className="py-2 pr-3">Mechanism</th>
              <th className="py-2 pr-3">Cargo bp</th><th className="py-2 pr-3">Tier</th>
              <th className="py-2">Human activity</th></tr></thead>
            <tbody>
              {shown.map((r, i) => (
                <tr key={i} className="border-b border-line/50">
                  <td className="py-2 pr-3 font-medium">{r.representative_system}</td>
                  <td className="py-2 pr-3 text-fg-dim">{r.family}</td>
                  <td className="py-2 pr-3"><Pill color={confColor[r.confidence] || "var(--muted)"}>{r.confidence}</Pill></td>
                  <td className="py-2 pr-3 text-fg-dim">{r.mechanism_bucket || "n/a"}</td>
                  <td className="py-2 pr-3 tabular-nums">{r.cargo_capacity_bp ?? "n/a"}</td>
                  <td className="py-2 pr-3">{r.reachability_tier ?? "n/a"}</td>
                  <td className="py-2 text-fg-dim">{r.human_cell_activity ?? "n/a"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="mt-3 text-[11px] text-fg-faint">{coverage?.disclaimer}</p>
      </Card>
    </div>
  );
}
