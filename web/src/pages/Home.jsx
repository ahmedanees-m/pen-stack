// The landing page: what PEN-STACK is, what it computes, and where to begin. Pulls live status so the hero shows
// the deployed version + tool count. Every claim here is also enforced by the engine (no fabrication, scope ledger).
import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api.js";
import { Icon } from "../components/icons.jsx";

const STAGES = [
  { to: "/writespec", icon: "writespec", k: "Intent", t: "Describe a write", d: "Plain language to a typed, ontology-backed WriteSpec, every field shows its provenance." },
  { to: "/site-finder", icon: "site", k: "Where", t: "Find the site", d: "Score loci by safety, durability and reachability for an edit intent." },
  { to: "/atlas", icon: "atlas", k: "Writer", t: "Pick the enzyme", d: "Compare writer families: capacity, programmability, DSB-freeness, human-cell activity." },
  { to: "/delivery", icon: "delivery", k: "Delivery", t: "Deliver & screen immunity", d: "Vehicle recommendation plus a five-axis immune-risk profile, never collapsed." },
  { to: "/offtarget", icon: "offtarget", k: "Off-target", t: "Nominate off-targets", d: "A real-data calibrated risk band, with the assay that would confirm each candidate." },
  { to: "/design", icon: "verify", k: "Design Studio", t: "Verify or generate", d: "Audit one design across three separate axes with a repairable proof, or sweep your goal for legal, screened candidates." },
  { to: "/guardian", icon: "guardian", k: "Biosecurity", t: "Guardian screen", d: "A dual-use gate: clear / flag / escalate / refuse, with an audit note." },
  { to: "/twin", icon: "twin", k: "Outcome", t: "Calibrated prediction", d: "OOD-gated outcome with a calibrated, widening interval, bounded by what is knowable." },
  { to: "/oracles", icon: "oracles", k: "Oracles", t: "Foundation-model mesh", d: "Structure, sequence, regulatory and affinity oracles under one result contract." },
  { to: "/experiments", icon: "experiments", k: "Loop", t: "Design the next experiment", d: "The most-informative batch, and the campaign that targets the first validated axis." },
];

const PILLARS = [
  { icon: "check", t: "Grounded, not generated", d: "Every number is computed by a validated tool or an OOD-gated oracle. The narrator never sources a value." },
  { icon: "spark", t: "Candidates, not claims", d: "Generative outputs are hypotheses; calling them a claim raises. A proposal must pass verification first." },
  { icon: "scope", t: "It tells you what it can't", d: "Outputs outside scope are returned as known-unknowns or extrapolating, listed explicitly, never guessed." },
  { icon: "twin", t: "Calibrated uncertainty", d: "Intervals that widen out of distribution, and cross-oracle disagreement widens them further. No false precision." },
];

const REPO = "https://github.com/ahmedanees-m/pen-stack";

export default function Home() {
  const [meta, setMeta] = useState(null);
  useEffect(() => {
    Promise.all([api.health().catch(() => null), api.capabilities().catch(() => null)])
      .then(([h, c]) => setMeta({ version: h?.version, tools: (c?.tools || c?.capabilities || []).length }));
  }, []);

  return (
    <div className="space-y-12 pb-6">
      {/* hero */}
      <section className="grid-bg relative overflow-hidden rounded-2xl border border-line bg-ink-900/40 px-6 py-12 sm:px-10 sm:py-16">
        <div className="relative max-w-3xl rise">
          <div className="mb-4 inline-flex items-center gap-2 rounded-full border border-brand/25 bg-brand/10 px-3 py-1 text-xs text-brand">
            <span className="h-1.5 w-1.5 rounded-full bg-ok" />
            {meta?.version ? `Live · v${meta.version}` : "Open infrastructure for genome writing"}
            {meta?.tools ? <span className="text-fg-faint">· {meta.tools} grounded tools</span> : null}
          </div>
          <h1 className="text-3xl font-semibold leading-tight tracking-tight sm:text-5xl">
            A grounded co-scientist for <span className="text-brand">genome writing</span>.
          </h1>
          <p className="mt-4 max-w-2xl text-base text-fg-dim sm:text-lg">
            Design, verify and de-risk genomic write operations end to end, from a plain-language goal to a
            verified, deliverable design, under one hard invariant: <strong className="text-fg">no fabrication</strong>.
            Every number is tool-computed; anything outside scope is labelled, never guessed.
          </p>
          <div className="mt-7 flex flex-wrap items-center gap-3">
            <Link to="/chat" className="btn-primary">Open the co-scientist <Icon name="arrow" size={16} /></Link>
            <Link to="/writespec" className="btn-secondary">Describe a write</Link>
            <a href={REPO} target="_blank" rel="noreferrer" className="btn-ghost"><Icon name="github" size={16} /> GitHub</a>
          </div>
          <p className="mt-4 text-xs text-fg-faint">Decision-support for research, not a clinical directive · MIT-licensed · single open package.</p>
        </div>
      </section>

      {/* the pipeline */}
      <section>
        <div className="mb-5">
          <div className="eyebrow">The pipeline</div>
          <h2 className="mt-1 text-xl font-semibold tracking-tight">Ten stages, each a calibrated, callable tool</h2>
          <p className="mt-1 max-w-2xl text-sm text-fg-dim">From intent to a closed validation loop. Open any stage to run it directly, or ask the co-scientist to compose them for you.</p>
        </div>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {STAGES.map((s) => (
            <Link key={s.to} to={s.to} className="card card-hover group p-4">
              <div className="flex items-center gap-2.5">
                <span className="grid h-9 w-9 place-items-center rounded-lg bg-brand/10 text-brand"><Icon name={s.icon} size={18} /></span>
                <div>
                  <div className="text-[10.5px] uppercase tracking-wider text-fg-faint">{s.k}</div>
                  <div className="text-sm font-semibold text-fg">{s.t}</div>
                </div>
                <Icon name="arrow" size={15} className="ml-auto text-fg-faint transition-transform group-hover:translate-x-0.5 group-hover:text-brand" />
              </div>
              <p className="mt-2.5 text-xs leading-relaxed text-fg-dim">{s.d}</p>
            </Link>
          ))}
        </div>
      </section>

      {/* the discipline */}
      <section>
        <div className="mb-5">
          <div className="eyebrow">Why trust it</div>
          <h2 className="mt-1 text-xl font-semibold tracking-tight">The no-fabrication spine</h2>
          <p className="mt-1 max-w-2xl text-sm text-fg-dim">The product is a traceable answer, or an explicit refusal, never a fabricated one. Four rules run through every surface.</p>
        </div>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {PILLARS.map((p) => (
            <div key={p.t} className="card p-4">
              <span className="grid h-9 w-9 place-items-center rounded-lg bg-ink-800 text-brand"><Icon name={p.icon} size={18} /></span>
              <h3 className="mt-3 text-sm font-semibold">{p.t}</h3>
              <p className="mt-1 text-xs leading-relaxed text-fg-dim">{p.d}</p>
            </div>
          ))}
        </div>
      </section>

      {/* CTA band */}
      <section className="rounded-2xl border border-brand/20 bg-gradient-to-br from-brand/10 to-transparent px-6 py-8 sm:px-10">
        <div className="flex flex-col items-start justify-between gap-4 sm:flex-row sm:items-center">
          <div>
            <h2 className="text-lg font-semibold tracking-tight">Start with a goal in plain language</h2>
            <p className="mt-1 max-w-xl text-sm text-fg-dim">The co-scientist parses it, runs the verifier, the Guardian and the immune profiler, and explains the result, grounding every number and listing what it cannot tell you.</p>
          </div>
          <Link to="/chat" className="btn-primary shrink-0">Open the co-scientist <Icon name="arrow" size={16} /></Link>
        </div>
      </section>

      {/* footer */}
      <footer className="hairline pt-6 text-sm text-fg-dim">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-center gap-2.5">
            <span className="grid h-7 w-7 place-items-center rounded-lg bg-brand/15 text-brand"><Icon name="dna" size={15} /></span>
            <span><strong className="text-fg">PEN-STACK</strong>{meta?.version ? ` · v${meta.version}` : ""} · MIT</span>
          </div>
          <div className="flex flex-wrap items-center gap-x-5 gap-y-2 text-xs">
            <a className="link" href={REPO} target="_blank" rel="noreferrer">GitHub</a>
            <a className="link" href="https://pypi.org/project/pen-stack/" target="_blank" rel="noreferrer">PyPI</a>
            <a className="link" href={`${REPO}/tree/main/docs`} target="_blank" rel="noreferrer">Docs</a>
            <Link className="link" to="/scope">Scope & known-unknowns</Link>
          </div>
        </div>
        <p className="mt-4 text-[11px] text-fg-faint">Decision-support for genome-writing research. Not a clinical directive. Every number is tool-sourced; what the engine cannot compute is listed, never guessed.</p>
      </footer>
    </div>
  );
}
