# Which writer reaches locus Z?

**Goal:** given a genomic locus, list the writer families/systems that can physically engage it, with
their reachability tier and therapeutic readiness.

The cross-link joins the Writable Genome's per-locus `reachable_tier1` annotation to the Writer Atlas.

## Python

```python
from pen_stack.atlas import crosslink as cl

# AAVS1 = PPP1R12C, chr19 ~55,090,914 -> 1 kb bin 55090
w = cl.writers_for_locus("chr19", 55090, ct="k562")
print(sorted(set(w["family"])))          # ['Cas12a', 'Cas9', 'bridge_IS110']
print(w["locus_writability"].iloc[0])    # 0.903 (validated safe harbour -> highly writable)
```

## CLI

```bash
pen-stack crosslink --chrom chr19 --bin 55090 --ct k562
```

## REST

```bash
curl 'http://localhost:8000/crosslink/writers?chrom=chr19&bin=55090&ct=k562'
```

## Reachability tiers

| Tier | Meaning | Families (v1) |
|---|---|---|
| **Tier 1** | directly scannable (high confidence) | bridge_IS110, seek_IS1111, PE_integrase, Cas9, Cas12a |
| **Tier 2** | context-dependent **candidate - requires validation** | CAST_VK, serine_integrase |
| **Tier 3** | not yet genome-scale predictable | TnpB_Fanzor |

Reachability is released at the **locus** level in v1 (Tier-1 reprogrammable families are near-universal
at 1 kb). Per-site reachability (does a specific bridge core exist here?) is computed by the Write
Planner (Phase 3) and the bridge off-target engine (Phase 1.5).
