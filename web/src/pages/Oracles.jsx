// Oracle Mesh: the foundation-model oracles under one contract. The table shows, per oracle, how it executes,
// its latency class, whether it is live, and its PUBLISHED reliability (reported verbatim from public benchmarks
// with citations, never a claim about this stack's own accuracy). Below it, a protein-ligand binding-affinity
// query (Boltz-2 head): every output is a CANDIDATE with native uncertainty, cache-or-abstain; protein-protein
// and protein-DNA pairs are flagged out-of-scope. Cross-oracle disagreement widens the reported interval.
import React, { useEffect, useState } from "react";
import ScoreGuide from "../components/ScoreGuide.jsx";
import { api } from "../api.js";
import { Card, Button, Spinner, ErrorNote, Field, Select } from "../components/ui.jsx";
import { num } from "../lib/format.js";

const LIVE = { true: "text-emerald-400", false: "text-fg-faint" };
const PAIR_TYPES = [
  { value: "inducer_switch", label: "Inducer switch (writer on/off)" },
  { value: "capsid_ligand", label: "Capsid-binding ligand" },
  { value: "effector_drug", label: "Effector drug" },
  { value: "ligand", label: "Generic protein + ligand" },
  { value: "protein_dna", label: "Protein-DNA (out of scope)" },
  { value: "protein_protein", label: "Protein-protein (out of scope)" },
];
// ERT2 ligand-binding domain (human ESR1, UniProt P03372 res 305-554) + 4-hydroxytamoxifen, the inducible-writer switch.
const ERT2_LBD =
  "SLALSLTADQMVSALLDAEPPILYSEYDPTRPFSEASMMGLLTNLADRELVHMINWAKRVPGFVDLTLHDQVHLLECAWLEILMIGLVWRSMEHPGKLLFAPNLLLDRNQGKCVEGMVEIFDMLLATSSRFRMMNLQGEEFVCLKSIILLNSGVYTFLSSTLKSLEEKDHIHRVLDKITDTLIHLMAKAGLTLQQQHQRLAQLLLILSHIRHMSNKGMEHLYSMKCKNVVPLYDLLLEMLDAHRLHAPTS";
const OHT_SMILES = "CCC(=C(C1=CC=C(C=C1)O)C2=CC=C(C=C2)OCCN(C)C)C3=CC=CC=C3";

function Reliability({ records }) {
  if (!records || records.length === 0) return <span className="text-fg-faint">n/a</span>;
  return (
    <ul className="space-y-1">
      {records.filter((r) => r.benchmark).map((r, i) => (
        <li key={i} className="text-[11px] text-fg-dim">
          <span className="text-fg">{r.metric}</span>{" = "}
          <b>{r.value == null ? "see source" : num(r.value)}</b>
          {r.reported_by ? <span className="text-fg-faint"> ({r.reported_by})</span> : null}
          {" on "}{r.benchmark}
          {r.citation?.length ? <span className="text-fg-faint"> [{r.citation.join(", ")}]</span> : null}
        </li>
      ))}
    </ul>
  );
}

export default function Oracles() {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  // affinity query
  const [protein, setProtein] = useState(ERT2_LBD);
  const [smiles, setSmiles] = useState(OHT_SMILES);
  const [pairType, setPairType] = useState("inducer_switch");
  const [aff, setAff] = useState(null);
  const [busy, setBusy] = useState(false);
  const [affErr, setAffErr] = useState(null);

  useEffect(() => {
    api.oracles().then(setData).catch(setError);
  }, []);

  const canQuery = protein.trim() && smiles.trim();

  async function runAffinity() {
    if (!canQuery) return;
    setBusy(true); setAffErr(null); setAff(null);
    try {
      setAff(await api.oracleAffinity({ protein_seq: protein, ligand_smiles: smiles, pair_type: pairType }));
    } catch (e) { setAffErr(e); } finally { setBusy(false); }
  }

  const summary = data?.summary;
  const oracles = data?.oracles || {};
  const dti = summary?.disagreement_to_interval;
  const v = aff?.value;

  return (
    <div className="space-y-4">
      <ScoreGuide
        intro="Every oracle answers through one contract: a value, its provenance, its OWN native uncertainty, and a scope card. Outputs are candidates / hypotheses, never ground truth."
        items={[
          { term: "Reliability", scale: "published, verbatim", meaning: "The wrapped model's PUBLISHED benchmark accuracy, reported verbatim WITH a citation. It is NOT a claim about this stack's accuracy and is NOT re-computed here; null means a verbatim score was not verified." },
          { term: "Native uncertainty", scale: "the model's own", meaning: "Surfaced, not hidden (e.g. half the spread between Boltz-2's two affinity heads). Cross-oracle disagreement widens the reported interval." },
          { term: "Affinity value", scale: "log(IC50), lower = stronger", meaning: "A binder probability + a predicted affinity (a prediction, not a measured Kd). Protein-protein / protein-DNA pairs are out of scope (flagged)." },
        ]}
        caveats={[
          "Held oracles (AF3 / Chai-1 / Protenix over full complexes) are cache-or-abstain, never run on the request path.",
        ]} />

      <Card title="Oracle mesh" subtitle="Every wrapped foundation model answers through one contract: a value, its provenance, its own native uncertainty, and a scope card. Outputs are candidates, never ground truth.">
        {error && <ErrorNote error={error} />}
        {!data && !error && <Spinner label="Loading oracle status…" />}
        {summary && (
          <div className="space-y-2 text-xs text-fg-dim">
            <p>{summary.note}</p>
            {dti && (
              <p>
                Cross-oracle disagreement widens the reported interval{" "}
                <b className={dti.monotone_nondecreasing ? "text-emerald-400" : "text-red-400"}>
                  {dti.monotone_nondecreasing ? "monotonically" : "non-monotonically (mechanism broken)"}
                </b>{" "}
                with the spread ({dti.native_uncertainty?.map((u) => num(u)).join(" -> ")}).
              </p>
            )}
            {summary.reliability_note && <p className="text-fg-faint">{summary.reliability_note}</p>}
          </div>
        )}
      </Card>

      {data && (
        <Card title="Oracles" subtitle="Execution, latency and live status, with PUBLISHED reliability reported verbatim from public benchmarks.">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead><tr className="border-b border-line text-left text-[11px] uppercase tracking-wide text-fg-faint">
                <th className="py-2 pr-3">Oracle</th><th className="py-2 pr-3">Execution</th>
                <th className="py-2 pr-3">Latency</th><th className="py-2 pr-3">Live</th>
                <th className="py-2">Published reliability</th></tr></thead>
              <tbody>
                {Object.entries(oracles).map(([name, s]) => (
                  <tr key={name} className="border-b border-line/50 align-top">
                    <td className="py-2 pr-3 font-mono text-xs">{name}</td>
                    <td className="py-2 pr-3 text-xs">{s.execution}</td>
                    <td className="py-2 pr-3 text-xs">{s.latency_class}</td>
                    <td className={`py-2 pr-3 text-xs ${LIVE[String(s.live)]}`}>{s.live ? "live" : "off"}</td>
                    <td className="py-2"><Reliability records={s.reliability} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      <Card title="Binding affinity (Boltz-2)" subtitle="Protein + small-molecule ligand. A candidate binder probability and predicted affinity with native uncertainty; the long GPU job runs off-request and is cached, so the request path is cache-or-abstain.">
        <div className="grid gap-3">
          <Field label="Protein sequence"><textarea className="input font-mono text-xs h-24" value={protein} onChange={(e) => setProtein(e.target.value)} /></Field>
          <Field label="Ligand SMILES"><input className="input font-mono text-xs" value={smiles} onChange={(e) => setSmiles(e.target.value)} /></Field>
          <Field label="Pair type"><Select value={pairType} onChange={setPairType} options={PAIR_TYPES} /></Field>
        </div>
        <div className="mt-4 flex items-center gap-3">
          <Button onClick={runAffinity} disabled={busy || !canQuery}>Query affinity</Button>
          {!canQuery && <span className="text-[11px] text-fg-faint">Provide a protein sequence and a ligand SMILES.</span>}
        </div>
        <p className="mt-2 text-[11px] text-amber-300/80">The Boltz-2 affinity head is protein-ligand only; protein-protein and protein-DNA pairs are returned as out-of-scope (extrapolating).</p>

        {busy && <div className="mt-3"><Spinner label="Querying the affinity oracle…" /></div>}
        {affErr && <div className="mt-3"><ErrorNote error={affErr} /></div>}
        {aff && (
          <div className="mt-3 rounded border border-line p-3 text-sm">
            {aff.extrapolating && <p className="mb-2 text-amber-300">Out of scope for the protein-ligand affinity head: {aff.note}</p>}
            {aff.available ? (
              <div className="space-y-1">
                <p>Binder probability: <b className="tabular-nums">{num(v?.binder_probability)}</b></p>
                <p>Predicted affinity value: <b className="tabular-nums">{num(v?.affinity_pred_value)}</b> <span className="text-[11px] text-fg-faint">({v?.units})</span></p>
                <p>Native uncertainty: <b className="tabular-nums">{num(aff.native_uncertainty)}</b> <span className="text-[11px] text-fg-faint">({v?.native_uncertainty_source})</span></p>
                <p className="text-[11px] text-fg-faint">{aff.cached ? "replayed from the committed oracle cache" : ""}{aff.note ? ` (${aff.note})` : ""}</p>
              </div>
            ) : (
              <p className="text-fg-dim">Cache-or-abstain: no cached run for these inputs, and the long GPU job never runs on the request path. {aff.note}</p>
            )}
          </div>
        )}
      </Card>
    </div>
  );
}
