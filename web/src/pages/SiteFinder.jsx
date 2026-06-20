// Site Finder, score loci for a gene by safety × durability × writability, and rank concrete write plans for an
// edit intent. Atlas-dependent: without the Phase-1 writability atlas the engine returns 503 (and we say so,
// never a fabricated locus).
import React, { useState } from "react";
import { api } from "../api.js";
import { Card, Button, Spinner, ErrorNote, Field, Select } from "../components/ui.jsx";
import { INTENTS, CELLS } from "../components/DesignForm.jsx";
import ConfidenceBand from "../components/ConfidenceBand.jsx";
import { num } from "../lib/format.js";

export default function SiteFinder() {
  const [gene, setGene] = useState("CCR5");
  const [ct, setCt] = useState("k562");
  const [intent, setIntent] = useState("safe_harbour_insertion");
  const [cargo, setCargo] = useState(2000);
  const [loci, setLoci] = useState(null);
  const [plans, setPlans] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);

  async function run() {
    setBusy(true); setError(null); setLoci(null); setPlans(null);
    try {
      const [w, p] = await Promise.allSettled([api.writable(gene, ct, 20), api.plan(gene, intent, cargo, ct, 6)]);
      if (w.status === "fulfilled") setLoci(w.value.loci || []);
      if (p.status === "fulfilled") setPlans(p.value.plans || []);
      if (w.status === "rejected" && p.status === "rejected") throw w.reason;
    } catch (e) { setError(e); } finally { setBusy(false); }
  }

  return (
    <div className="space-y-4">
      <Card title="Find writable sites" subtitle="Loci scored by safety, durability, and writability for a target gene.">
        <div className="grid gap-3 sm:grid-cols-4">
          <Field label="Gene"><input className="input" value={gene} onChange={(e) => setGene(e.target.value)} /></Field>
          <Field label="Cell type"><Select value={ct} onChange={setCt} options={CELLS} /></Field>
          <Field label="Edit intent"><Select value={intent} onChange={setIntent} options={INTENTS.map((v) => ({ value: v, label: v.replace(/_/g, " ") }))} /></Field>
          <Field label="Cargo bp"><input className="input" type="number" value={cargo} onChange={(e) => setCargo(parseInt(e.target.value || "0", 10))} /></Field>
        </div>
        <div className="mt-4"><Button onClick={run} disabled={busy}>Score sites</Button></div>
      </Card>

      {busy && <Card><Spinner label="Scanning the writability atlas…" /></Card>}
      {error && <Card><ErrorNote error={error} /></Card>}

      {loci && (
        <Card title={`Writable loci for ${gene}`} subtitle={`${loci.length} candidate loci · ${ct}`}>
          {loci.length === 0 ? <p className="text-sm text-fg-faint">No loci returned.</p> : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead><tr className="border-b border-line text-left text-[11px] uppercase tracking-wide text-fg-faint">
                  <th className="py-2 pr-3">Locus</th><th className="py-2 pr-3">Safety</th>
                  <th className="py-2 pr-3 w-44">Durability</th><th className="py-2">Writability</th></tr></thead>
                <tbody>
                  {loci.map((l, i) => (
                    <tr key={i} className="border-b border-line/50">
                      <td className="py-2 pr-3 font-mono text-xs">{l.chrom}:bin{l.bin}</td>
                      <td className="py-2 pr-3 tabular-nums">{num(l.safety)}</td>
                      <td className="py-2 pr-3"><ConfidenceBand point={l.p_durable} status="grounded" /></td>
                      <td className="py-2 tabular-nums text-brand">{num(l.writability)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>
      )}

      {plans && (
        <Card title="Ranked write plans" subtitle="Traceable plans for the chosen edit intent.">
          {plans.length === 0 ? <p className="text-sm text-fg-faint">No plans returned.</p> : (
            <ol className="space-y-2">
              {plans.map((p, i) => (
                <li key={i} className="rounded-lg border border-line bg-ink-900 p-3 text-sm">
                  <div className="flex items-center justify-between">
                    <span className="font-medium">{i + 1}. {p.writer} → {p.site?.chrom}:bin{p.site?.bin}</span>
                    <span className="text-xs tabular-nums text-brand">score {num(p.score)}</span>
                  </div>
                  <div className="mt-1 flex flex-wrap gap-3 text-[11px] text-fg-dim">
                    <span>safety {num(p.safety)}</span><span>durability {num(p.durability)}</span>
                    <span>writer activity {num(p.writer_activity)}</span><span>on-target {num(p.on_target)}</span>
                    {p.reachability_tier && <span>tier {p.reachability_tier}</span>}
                  </div>
                </li>
              ))}
            </ol>
          )}
        </Card>
      )}
    </div>
  );
}
