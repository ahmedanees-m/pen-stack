// Challenge, the open, recurring, held-out Genome-Writing Challenge. Public tasks (no labels) + the PEN-STACK
// reference leaderboard. Submissions are scored OFFLINE against held-out labels (never accepted over HTTP), so
// this page only exposes the round and the anchor score.
import React, { useEffect, useState } from "react";
import { api } from "../api.js";
import { Card, Spinner, ErrorNote, Pill, Stat } from "../components/ui.jsx";
import { pct, titleCase } from "../lib/format.js";

export default function Challenge() {
  const [lb, setLb] = useState(null);
  const [tasks, setTasks] = useState(null);
  const [busy, setBusy] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    (async () => {
      try {
        const [l, t] = await Promise.all([api.challengeLeaderboard(), api.challengeTasks()]);
        setLb(l); setTasks(t.tasks || []);
      } catch (e) { setError(e); } finally { setBusy(false); }
    })();
  }, []);

  if (busy) return <Card><Spinner label="Loading the challenge round…" /></Card>;
  if (error) return <Card title="Challenge"><ErrorNote error={error} /></Card>;

  const ref = lb?.leaderboard?.[0];
  return (
    <div className="space-y-4">
      <Card title={`Genome-Writing Challenge · ${lb?.round}`}
            subtitle="The CASP / Virtual-Cell-Challenge model for the writing side: held-out labels, no circular scoring.">
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <Stat label="Tasks" value={ref?.n_tasks} />
          <Stat label="Reference aggregate" value={pct(ref?.aggregate)} color="var(--ok)" />
          <Stat label="Circular labels" value={ref?.no_circular_labels ? "none" : "present"} color={ref?.no_circular_labels ? "var(--ok)" : "var(--bad)"} />
          <Stat label="No-fabrication" value={ref?.no_fabrication ? "audited" : "pending"} color="var(--ok)" />
        </div>
      </Card>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card title="Leaderboard" subtitle="Anchored by the PEN-STACK reference submission; external rows appended after a round.">
          <table className="w-full text-sm">
            <thead><tr className="border-b border-line text-left text-[11px] uppercase tracking-wide text-fg-faint">
              <th className="py-2 pr-3">Submission</th><th className="py-2 pr-3">Aggregate</th><th className="py-2">By family</th></tr></thead>
            <tbody>
              {(lb?.leaderboard || []).map((row, i) => (
                <tr key={i} className="border-b border-line/50">
                  <td className="py-2 pr-3 font-medium">{row.submission}</td>
                  <td className="py-2 pr-3 tabular-nums text-brand">{pct(row.aggregate)}</td>
                  <td className="py-2"><div className="flex flex-wrap gap-1">
                    {Object.entries(row.by_family || {}).map(([f, s]) => <Pill key={f}>{f}: {pct(s)}</Pill>)}
                  </div></td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="mt-3 text-[11px] text-fg-faint">Labels: {lb?.rules?.labels}. A fabricated answer simply scores
            0, it cannot match a validated held-out label by inventing one.</p>
        </Card>

        <Card title="Public tasks" subtitle="What a submission sees: the family + design, never the label.">
          <ul className="space-y-2">
            {(tasks || []).map((t) => (
              <li key={t.id} className="rounded-lg border border-line bg-ink-900 p-3">
                <div className="flex items-center justify-between">
                  <span className="font-mono text-xs text-fg">{t.id}</span>
                  <Pill color="var(--brand)">{titleCase(t.family)}</Pill>
                </div>
                <p className="mt-1 text-[11px] text-fg-dim">{t.public_input?.instructions}</p>
              </li>
            ))}
          </ul>
        </Card>
      </div>
    </div>
  );
}
