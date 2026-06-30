// A shared design builder used by Design Studio / Delivery & Immunity / Twin. Produces the `design` dict the
// engine expects. The vocabularies below mirror the engine's accepted values; the form adds no science, it just
// assembles the request the typed API validates.
//
// v7.1.5: the Chromosome field is a controlled dropdown (no free-text typos like "chrZZZ" can be entered) and is
// gene/chromosome concordance-checked against the engine: when the entered chromosome does not match the named
// gene's canonical location (e.g. BRCA1 is on chr17, not chr1), an inline warning + a one-click fix is shown.
// The chromosome does NOT move the scored locus (scoring is indexed by the gene's resolved coordinates) - the
// concordance check is the meaningful chromosome-level signal.
import React, { useEffect, useState } from "react";
import { Field, Select } from "./ui.jsx";
import { api } from "../api.js";

export const VEHICLES = [
  "AAV_single", "AAV_dual", "lentivirus", "lnp_mrna", "helper_dependent_adenovirus", "hsv_amplicon", "electroporation",
];
export const INTENTS = [
  "safe_harbour_insertion", "knock_in_with_disruption", "high_durability_insertion",
  "regulatory_element_excision", "landing_pad_insertion", "repeat_excision",
];
// A clearly-labelled EXAMPLE cassette fragment (GFP CDS opening) so a user can see the innate-sensing axis compute;
// real use pastes the actual cargo sequence. It is an example, not a default, and is never auto-applied.
export const EXAMPLE_CARGO_SEQ =
  "ATGGTGAGCAAGGGCGAGGAGCTGTTCACCGGGGTGGTGCCCATCCTGGTCGAGCTGGACGGCGACGTAAACGGCCACAAGTTCAGCGTGTCCGGCGAGGGC";
export const CELLS = ["k562", "hepg2", "hspc", "h1_hesc", "ipsc", "cd8_t", "pbmc"];
export const CHROMS = [...Array(22).keys()].map((i) => `chr${i + 1}`).concat(["chrX", "chrY", "chrM"]);

export const DEFAULT_DESIGN = {
  write_type: "insertion", gene: "AAVS1", chrom: "chr19", delivery_vehicle: "AAV_single",
  cargo_bp: 3000, cargo_function: "human factor IX", cell_type: "k562", in_vivo: true,
  // cargo_seq is intentionally empty (no fabricated sequence) until the user pastes one (powers the innate axis).
  // The writer enzyme is chosen on the Writer Atlas page (where its immunogenicity is profiled), not here.
  cargo_seq: "",
};

// only K562 / HepG2 / HSPC have a measured writability atlas; the rest are a declared, data-gated roadmap. The
// dropdown shows this so a no-atlas cell type is not silently indistinguishable from a measured one (v7.1.5).
const _COV_LABEL = { full: "full atlas", partial: "partial atlas", none: "no atlas" };

export default function DesignForm({ design, onChange, showCargoFunction = true, showCargoSeq = true }) {
  const set = (k, v) => onChange({ ...design, [k]: v });
  // canonical chrom of the gene: a string if found, null if the gene is unknown, undefined before the check.
  const [geneChrom, setGeneChrom] = useState(undefined);
  // cell-type options labelled with their writability-atlas coverage (from /api/celltypes); plain list as fallback.
  const [cellOpts, setCellOpts] = useState(CELLS);
  const [cellCov, setCellCov] = useState(null);

  useEffect(() => {
    let live = true;
    api.celltypes()
      .then((r) => {
        const list = (r && (r.cell_types || r)) || [];
        if (!live || !Array.isArray(list) || !list.length) return;
        setCellCov(Object.fromEntries(list.map((c) => [c.id, c.coverage])));
        setCellOpts(list.map((c) => ({ value: c.id, label: `${c.label || c.id} · ${_COV_LABEL[c.coverage] || c.coverage}` })));
      })
      .catch(() => {});
    return () => { live = false; };
  }, []);

  // gene/chromosome concordance: resolve the gene's canonical chromosome (debounced) so we can warn on a mismatch.
  useEffect(() => {
    const g = (design.gene || "").trim();
    if (!g) { setGeneChrom(undefined); return; }
    let live = true;
    const t = setTimeout(() => {
      api.geneLocation(g)
        .then((r) => { if (live) setGeneChrom(r.found ? r.chrom : null); })
        .catch(() => { if (live) setGeneChrom(undefined); });
    }, 300);
    return () => { live = false; clearTimeout(t); };
  }, [design.gene]);

  const mismatch = geneChrom && design.chrom && geneChrom !== design.chrom;

  return (
    <div className="grid gap-3 sm:grid-cols-2">
      <Field label="Gene / target"><input className="input" value={design.gene} onChange={(e) => set("gene", e.target.value)} /></Field>
      <Field label="Chromosome" hint={geneChrom ? `${design.gene} is on ${geneChrom}` : "chr1–chr22, chrX, chrY, chrM"}>
        <Select value={design.chrom} onChange={(v) => set("chrom", v)} options={CHROMS} />
        {mismatch && (
          <p className="mt-1 text-[12px]" style={{ color: "var(--warn)" }}>
            ⚠ {design.gene} is on <strong>{geneChrom}</strong>, not {design.chrom}. The chromosome does not move the
            scored locus (scoring uses the gene's canonical location).{" "}
            <button type="button" className="underline" onClick={() => set("chrom", geneChrom)}>Use {geneChrom}</button>
          </p>
        )}
        {geneChrom === null && (design.gene || "").trim() && (
          <p className="mt-1 text-[11px] text-fg-faint">{design.gene} is not in the coordinate table; concordance can't be confirmed.</p>
        )}
      </Field>
      <Field label="Delivery vehicle"
             hint={design.delivery_vehicle === "lnp_mrna" ? "PEGylated LNP — the anti-PEG axis applies (re-dosing barrier)" : "non-PEG vehicle — the anti-PEG axis abstains"}>
        <Select value={design.delivery_vehicle} onChange={(v) => set("delivery_vehicle", v)}
                options={VEHICLES.map((v) => ({ value: v, label: v.replace(/_/g, " ") }))} />
      </Field>
      <Field label="Cell type" hint={cellCov && design.cell_type
              ? (cellCov[design.cell_type] === "none"
                 ? "no measured writability atlas — locus scoring abstains for this cell type"
                 : `${_COV_LABEL[cellCov[design.cell_type]] || cellCov[design.cell_type]} (measured)`)
              : "K562 / HepG2 / HSPC have a measured atlas; others are a data-gated roadmap"}>
        <Select value={design.cell_type} onChange={(v) => set("cell_type", v)} options={cellOpts} />
      </Field>
      <Field label="Cargo size (bp)" hint="AAV single-vector payload caps near ~4.7 kb">
        <input className="input" type="number" min={0} max={200000} step={100} value={design.cargo_bp}
               onChange={(e) => { const n = parseInt(e.target.value || "0", 10);
                 set("cargo_bp", Number.isNaN(n) ? 0 : Math.min(200000, Math.max(0, n))); }} />
      </Field>
      <Field label="Context">
        <Select value={design.in_vivo ? "in_vivo" : "ex_vivo"} onChange={(v) => set("in_vivo", v === "in_vivo")}
                options={[{ value: "in_vivo", label: "in vivo" }, { value: "ex_vivo", label: "ex vivo" }]} />
      </Field>
      {showCargoFunction && (
        <div className="sm:col-span-2">
          <Field label="Cargo function" hint="Plain description; the Guardian screens this for dual-use hazard signal">
            <input className="input" value={design.cargo_function || ""} onChange={(e) => set("cargo_function", e.target.value)} />
          </Field>
        </div>
      )}
      {showCargoSeq && (
        <div className="sm:col-span-2">
          <Field label="Cargo sequence (optional)"
                 hint="Powers the innate-sensing axis (CpG/TLR9 for DNA, U-content + dsRNA for mRNA — the form follows the vehicle). Empty = the axis abstains, never a guessed value.">
            <textarea className="input font-mono text-[11px] leading-snug" rows={3}
                      placeholder="Paste the cargo / cassette nucleotide sequence (A/C/G/T or A/C/G/U)…"
                      value={design.cargo_seq || ""} onChange={(e) => set("cargo_seq", e.target.value)} />
            <div className="mt-1 flex items-center gap-3 text-[11px]">
              <button type="button" className="underline text-fg-faint hover:text-fg"
                      onClick={() => set("cargo_seq", EXAMPLE_CARGO_SEQ)}>insert example (GFP CDS fragment)</button>
              {design.cargo_seq ? (
                <button type="button" className="underline text-fg-faint hover:text-fg"
                        onClick={() => set("cargo_seq", "")}>clear</button>
              ) : null}
              {design.cargo_seq ? <span className="text-fg-faint tabular-nums">{design.cargo_seq.replace(/\s/g, "").length} nt</span> : null}
            </div>
          </Field>
        </div>
      )}
    </div>
  );
}
