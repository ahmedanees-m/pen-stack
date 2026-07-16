# The delivery palette (`configs/delivery_vehicles.yaml`), v3.3

Genome writing uses a *palette* of delivery vehicles; the substrate scores and constrains all of it (not just
dual-AAV). Eight vehicles, each with capacity, integration status, division dependence, an immunogenicity
*prior* (qualitative; the *magnitude* is a declared known-unknown, never predicted), re-dosability, tropism,
ex/in-vivo, compatible cargo form {DNA, mRNA, RNP}, and ≥1 DOI.

| Vehicle | Capacity | Integrating | Cargo form | Typical use |
|---|---|---|---|---|
| AAV (single) | ~4.7 kb | episomal | DNA | in vivo |
| AAV (dual) | ~9 kb | episomal | DNA | in vivo, split cargo |
| lentivirus | ~8 kb | **integrating** | DNA | ex vivo (CAR-T, HSPC) |
| helper-dependent adenovirus | ~35 kb | non-integrating | DNA | in vivo, large cargo |
| HSV amplicon | >100 kb | non-integrating | DNA | CNS, very large cargo |
| LNP, mRNA | large RNA | transient | mRNA / RNP | in vivo (liver-tropic) |
| eVLP | RNP | non-integrating | RNP | ex/in vivo |
| electroporation | no packaging limit | depends on cargo | DNA / mRNA / RNP | ex vivo |

The delivery **rules** (`configs/rules/delivery.yaml`) turn this into: **hard rejects** (cargo > capacity;
writer output-form ∉ vehicle cargo-form; non-integrating goal + integrating vehicle), **soft penalties**
(split-AAV, recombinogenic/packaging-hostile sequence), and a **scope flag** (immunogenicity magnitude +
precise tropism, not modeled). See `docs/verify.md`.
