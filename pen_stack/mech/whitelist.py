"""The InterPro-audited 18-family Pfam whitelist (imported from genome-atlas v1.2.1).

Tier-A of MECH-CLASS: maps a Pfam domain architecture to a mechanism bucket
(``DSB_NUCLEASE`` / ``DSB_FREE_TRANSEST_RECOMBINASE`` / ``TRANSPOSASE``) using domain presence plus
*composite co-occurrence rules* (e.g. Cas9 requires >=2 of its 3 signature domains; IS110 requires
both PF01548 and PF02371). This is the audited backbone the program carries forward (Section 9); the retired
ESM-2 "PEN-DISCOVER" head is not used - domain evidence is the load-bearing mechanism signal.

The source YAML ``pfam_whitelist.yaml`` is the genome-atlas asset, accessions verified against InterPro
on 2026-04-22 (v1.2.1 corrected three v1.2.0 accession errors).
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from pathlib import Path

import yaml

_WL_PATH = Path(__file__).resolve().parent / "pfam_whitelist.yaml"

# Composite architectures: a call is only "composite-grade" (highest confidence) when the required
# co-occurring domains are all present. Derived from the whitelist co_occurs_with fields.
_COMPOSITES = {
    "Cas9": {"min": 2, "of": {"PF13395", "PF18541", "PF16595"}, "bucket": "DSB_NUCLEASE"},
    "IS110_bridge": {"min": 2, "of": {"PF01548", "PF02371"}, "bucket": "DSB_FREE_TRANSEST_RECOMBINASE"},
}


@dataclass(frozen=True)
class MechCall:
    bucket: str | None         # mechanism bucket, or None if no whitelisted domain present
    confidence: str            # composite | single | conflicting | none
    basis: str                 # human-readable evidence trail
    matched: tuple[str, ...]   # whitelisted accessions that fired


class PfamWhitelist:
    def __init__(self, path: str | Path = _WL_PATH):
        doms = yaml.safe_load(Path(path).read_text(encoding="utf-8"))["domains"]
        self.bucket_of: dict[str, str] = {d["accession"]: d["mechanism_bucket"] for d in doms}
        self.name_of: dict[str, str] = {d["accession"]: d.get("name", "") for d in doms}
        self.version = "1.2.1"

    def classify(self, pfam_signature) -> MechCall:
        """Mechanism from a Pfam domain set - independent of any inherited/family label."""
        sig = {str(a).strip() for a in (pfam_signature or []) if str(a).strip()}
        hits = sorted(sig & set(self.bucket_of))
        if not hits:
            return MechCall(None, "none", "no whitelisted Pfam domain present", ())

        # composite rule wins (most specific, highest confidence)
        for name, rule in _COMPOSITES.items():
            present = sig & rule["of"]
            if len(present) >= rule["min"]:
                return MechCall(rule["bucket"], "composite",
                                f"{name}: {len(present)}/{len(rule['of'])} signature domains "
                                f"({','.join(sorted(present))})", tuple(hits))

        buckets = Counter(self.bucket_of[a] for a in hits)
        top, n = buckets.most_common(1)[0]
        if len(buckets) > 1:
            return MechCall(top, "conflicting",
                            f"mixed domain evidence: {dict(buckets)}", tuple(hits))
        return MechCall(top, "single",
                        f"single-bucket domain evidence: {','.join(hits)}", tuple(hits))
