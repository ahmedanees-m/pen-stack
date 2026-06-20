// A shared design builder used by Verify / Guardian / Delivery & Immunity / Twin. Produces the `design` dict the
// engine expects. The vocabularies below mirror the engine's accepted values; the form adds no science, it just
// assembles the request the typed API validates.
import React from "react";
import { Field, Select } from "./ui.jsx";

export const VEHICLES = [
  "AAV_single", "AAV_dual", "lentivirus", "lnp_mrna", "helper_dependent_adenovirus", "hsv_amplicon", "electroporation",
];
export const INTENTS = [
  "safe_harbour_insertion", "knock_in_with_disruption", "high_durability_insertion",
  "regulatory_element_excision", "landing_pad_insertion", "repeat_excision",
];
export const CELLS = ["k562", "hepg2", "hspc", "h1_hesc", "ipsc", "cd8_t", "pbmc"];

export const DEFAULT_DESIGN = {
  write_type: "insertion", gene: "AAVS1", chrom: "chr19", delivery_vehicle: "AAV_single",
  cargo_bp: 3000, cargo_function: "human factor IX", cell_type: "k562", in_vivo: true,
};

export default function DesignForm({ design, onChange, showCargoFunction = true }) {
  const set = (k, v) => onChange({ ...design, [k]: v });
  return (
    <div className="grid gap-3 sm:grid-cols-2">
      <Field label="Gene / target"><input className="input" value={design.gene} onChange={(e) => set("gene", e.target.value)} /></Field>
      <Field label="Chromosome"><input className="input" value={design.chrom} onChange={(e) => set("chrom", e.target.value)} /></Field>
      <Field label="Delivery vehicle">
        <Select value={design.delivery_vehicle} onChange={(v) => set("delivery_vehicle", v)}
                options={VEHICLES.map((v) => ({ value: v, label: v.replace(/_/g, " ") }))} />
      </Field>
      <Field label="Cell type">
        <Select value={design.cell_type} onChange={(v) => set("cell_type", v)} options={CELLS} />
      </Field>
      <Field label="Cargo size (bp)" hint="AAV single-vector payload caps near ~4.7 kb">
        <input className="input" type="number" value={design.cargo_bp}
               onChange={(e) => set("cargo_bp", parseInt(e.target.value || "0", 10))} />
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
    </div>
  );
}
