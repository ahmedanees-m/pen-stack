#!/usr/bin/env python3
"""Generate and verify the pre-registration SHA-256 manifest (Additional File 5).

Every pre-registration in `prereg/` is frozen by a companion `prereg/SHA256_LOCK_*.json`
lock that records, for each locked file, the SHA-256 of its committed bytes. This script
walks those locks, recomputes each hash from the committed file, and asserts it against the
recorded value; it then writes (or checks) `prereg/PREREG_MANIFEST.md`, the full manifest of
every lock entry plus the ten-row honesty-ledger subset cited in Table 3.

Modes:
  --check   (default) recompute every hash from the working tree and assert it matches the
            lock; regenerate the manifest in memory and assert it is byte-identical to the
            committed `prereg/PREREG_MANIFEST.md`; assert every Table 3 pre-registration is a
            locked file that re-hashes. Exit non-zero on any mismatch. This is what CI runs.
  --write   regenerate `prereg/PREREG_MANIFEST.md` from the locks and the ledger selection.

The honesty-ledger selection (which ten of the pre-registrations bear on the paper's claims)
is held in `prereg/honesty_ledger.json`; this script validates that every file it names is
locked and re-hashes, so the Table 3 citations cannot drift from the frozen bytes.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PREREG = ROOT / "prereg"
MANIFEST = PREREG / "PREREG_MANIFEST.md"
LEDGER = PREREG / "honesty_ledger.json"

# The phase-0 lock is the programme origin seal: it recorded the bytes of four inputs at the start of the
# programme, and all four were revised in later cycles, so their phase-0 hashes no longer match the current
# files. One input (configs/score_axes.yaml) stayed in use and is re-locked at its current bytes by the
# phase-2 lock; the other three were retired and are no longer referenced by any lock. The phase-0 entries are
# reported as superseded rather than re-hashed. The exemption is re-hash gated (see classify): an allowlisted
# entry counts as superseded only when its current bytes differ from the seal, so an entry that still matches
# its lock is asserted like any other and cannot be hidden by the allowlist. This is the ONLY lock exempted;
# every other lock must match the current committed bytes, so a genuine drift cannot be silently excused.
SUPERSEDED_LOCKS = {"SHA256_LOCK_phase0.json"}


def sha256_of(path: Path) -> str:
    """SHA-256 of a file's bytes, streamed so a large locked artifact needs no full read."""
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_locks() -> list[dict]:
    """Return one classified record per (lock file, locked file) entry, sorted for a deterministic manifest.

    Each record carries the workstream or phase identifier, the locked file path, the recorded SHA-256, and
    the SHA-256 recomputed from the working tree; classify() then tags it verified/superseded/relocked.
    """
    records: list[dict] = []
    for lock_path in sorted(PREREG.glob("SHA256_LOCK_*.json")):
        lock = json.loads(lock_path.read_text(encoding="utf-8"))
        registration = lock.get("workstream") or (
            f"phase {lock['phase']}" if "phase" in lock else lock_path.stem.replace("SHA256_LOCK_", "")
        )
        # ws and phase>=1 locks record their hashes under "sha256"; the phase-0 lock uses "locked_files".
        sha_map = lock.get("sha256") or lock.get("locked_files") or {}
        for locked_file, recorded in sorted(sha_map.items()):
            target = ROOT / locked_file
            records.append(
                {
                    "lock": lock_path.name,
                    "registration": registration,
                    "file": locked_file,
                    "recorded_sha256": recorded,
                    "recomputed_sha256": sha256_of(target) if target.is_file() else None,
                }
            )
    return classify(records)


def classify(records: list[dict]) -> list[dict]:
    """Tag each record verified / superseded / relocked_current.

    The phase-0 exemption is re-hash gated: an allowlisted entry counts as superseded only when its current
    bytes differ from the recorded seal. An allowlisted entry that still matches its lock is treated as
    verified and asserted like any other, so the allowlist cannot hide a live lock as superseded. `verified`
    means the current bytes match the recorded hash; `relocked_current` means the same file is recorded at its
    current bytes by some (possibly later-cycle) lock, i.e. a live lock still freezes it.
    """
    current_locked = {
        r["file"] for r in records
        if r["recomputed_sha256"] is not None and r["recomputed_sha256"] == r["recorded_sha256"]
    }
    for r in records:
        matches = r["recomputed_sha256"] is not None and r["recomputed_sha256"] == r["recorded_sha256"]
        r["superseded"] = (r["lock"] in SUPERSEDED_LOCKS) and not matches
        r["verified"] = matches and not r["superseded"]
        r["relocked_current"] = r["file"] in current_locked
    return records


def verify_records(records: list[dict]) -> list[str]:
    """Return human-readable failures; empty means every non-superseded locked file re-hashes.

    Superseded entries (an allowlisted phase-0 seal whose file was revised; see classify) are exempt from the
    re-hash assertion. The exemption is re-hash gated, so an allowlisted entry that still matches its lock is
    not superseded and is asserted here; the allowlist cannot silence a lock whose file still matches.
    """
    failures: list[str] = []
    for r in records:
        if r["superseded"]:
            continue
        if r["recomputed_sha256"] is None:
            failures.append(f"{r['lock']}: locked file {r['file']} is not present in the checkout")
        elif r["recomputed_sha256"] != r["recorded_sha256"]:
            failures.append(
                f"{r['lock']}: {r['file']} recorded {r['recorded_sha256'][:12]} "
                f"but recomputed {r['recomputed_sha256'][:12]}"
            )
    return failures


def load_ledger() -> list[dict]:
    if not LEDGER.is_file():
        raise FileNotFoundError(f"honesty-ledger selection not found at {LEDGER}")
    return json.loads(LEDGER.read_text(encoding="utf-8"))["claims"]


def verify_ledger(ledger: list[dict], by_file: dict[str, dict]) -> list[str]:
    """Assert each Table 3 claim cites a locked pre-registration that currently re-hashes."""
    failures: list[str] = []
    for claim in ledger:
        prereg_file = claim["prereg_file"]
        record = by_file.get(prereg_file)
        if record is None:
            failures.append(f"claim {claim['n']}: {prereg_file} is not a locked pre-registration")
        elif not record["verified"]:
            failures.append(f"claim {claim['n']}: {prereg_file} does not re-hash against its lock")
    return failures


def render_manifest(records: list[dict], ledger: list[dict]) -> str:
    """Render the deterministic Additional File 5 manifest as Markdown (no timestamps)."""
    lines: list[str] = []
    lines.append("# Additional File 5: pre-registration SHA-256 manifest")
    lines.append("")
    lines.append(
        "Every pre-registration in `prereg/` is frozen by a companion `SHA256_LOCK_*.json` that records "
        "the SHA-256 of the locked file's committed bytes. This manifest is generated and checked by "
        "`scripts/prereg_manifest.py`, which recomputes each hash from source and asserts it against the "
        "lock; the check runs in continuous integration on every commit and in `make repro`."
    )
    lines.append("")
    lines.append("Verify any row from a clean checkout:")
    lines.append("")
    lines.append("```")
    lines.append("sha256sum <file>            # must equal the SHA-256 column")
    lines.append("python scripts/prereg_manifest.py --check   # re-hash every entry, assert this manifest")
    lines.append("```")
    lines.append("")
    verified = [r for r in records if r["verified"]]
    superseded = [r for r in records if r["superseded"]]
    lines.append(f"Total: {len(records)} locked files across "
                 f"{len({r['lock'] for r in records})} pre-registration locks; "
                 f"{len(verified)} re-hash against the current committed bytes and are asserted here. "
                 f"{len(superseded)} belong to the superseded phase-0 origin seal (listed at the end).")
    lines.append("")

    lines.append("## Table 3 honesty-ledger pre-registrations")
    lines.append("")
    lines.append("The ten claims in Table 3, each with the committed pre-registration that fixed it before "
                 "scoring and that pre-registration's SHA-256.")
    lines.append("")
    lines.append("| # | Claim | Verdict | Pre-registration | SHA-256 |")
    lines.append("|---|---|---|---|---|")
    for claim in ledger:
        rec = next(r for r in verified if r["file"] == claim["prereg_file"])
        lines.append(
            f"| {claim['n']} | {claim['claim']} | {claim['verdict']} | "
            f"`{claim['prereg_file']}` | `{rec['recorded_sha256']}` |"
        )
    lines.append("")

    lines.append("## Full manifest: every current pre-registration lock")
    lines.append("")
    lines.append("Each file below re-hashes to the SHA-256 shown; `scripts/prereg_manifest.py` asserts this on "
                 "every commit.")
    lines.append("")
    lines.append("| Registration | Lock | File | SHA-256 |")
    lines.append("|---|---|---|---|")
    for r in verified:
        lines.append(
            f"| {r['registration']} | `{r['lock']}` | `{r['file']}` | `{r['recorded_sha256']}` |"
        )
    lines.append("")

    if superseded:
        relocked = [r for r in superseded if r["relocked_current"]]
        retired = [r for r in superseded if not r["relocked_current"]]
        lines.append("## Superseded phase-0 origin seal")
        lines.append("")
        para = (f"The phase-0 lock is the programme origin seal. All {len(superseded)} of its inputs were "
                f"revised in later cycles, so the phase-0 hashes below are the sealed originals and no longer "
                f"match the current files.")
        if relocked:
            para += (f" {len(relocked)} stayed in use and {'is' if len(relocked) == 1 else 'are'} re-locked at "
                     f"the current bytes by a later-cycle lock (asserted in the manifest above): "
                     + ", ".join(f"`{r['file']}`" for r in relocked) + ".")
        if retired:
            para += (f" The other {len(retired)} {'is' if len(retired) == 1 else 'are'} not re-locked at "
                     f"{'its' if len(retired) == 1 else 'their'} current bytes by any later lock, so only the "
                     f"phase-0 original"
                     + ("" if len(retired) == 1 else "s")
                     + f" {'is' if len(retired) == 1 else 'are'} recorded here: "
                     + ", ".join(f"`{r['file']}`" for r in retired) + ".")
        lines.append(para)
        lines.append("")
        lines.append("| Lock | File | Sealed SHA-256 (phase 0) | Current status |")
        lines.append("|---|---|---|---|")
        for r in superseded:
            status = "re-locked at current bytes above" if r["relocked_current"] else "not re-locked by a later lock"
            lines.append(f"| `{r['lock']}` | `{r['file']}` | `{r['recorded_sha256']}` | {status} |")
        lines.append("")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="regenerate prereg/PREREG_MANIFEST.md")
    args = parser.parse_args()

    records = load_locks()
    ledger = load_ledger()
    # A file can appear in more than one lock (an input re-locked in a later cycle); prefer the verified record.
    by_file: dict[str, dict] = {}
    for r in records:
        if r["file"] not in by_file or r["verified"]:
            by_file[r["file"]] = r

    failures = verify_records(records) + verify_ledger(ledger, by_file)
    if failures:
        print("PRE-REGISTRATION MANIFEST FAILED: locked bytes do not match their locks.")
        for f in failures:
            print(f"  [FAIL] {f}")
        return 1

    rendered = render_manifest(records, ledger)
    n_verified = sum(1 for r in records if r["verified"])
    n_superseded = sum(1 for r in records if r["superseded"])

    if args.write:
        MANIFEST.write_text(rendered, encoding="utf-8", newline="\n")
        print(f"Wrote {MANIFEST.relative_to(ROOT)}: {n_verified} locked files re-hash, "
              f"{n_superseded} superseded (phase-0 origin seal), "
              f"{len(ledger)} Table 3 pre-registrations cited.")
        return 0

    if not MANIFEST.is_file():
        print(f"{MANIFEST.relative_to(ROOT)} is missing; run `python scripts/prereg_manifest.py --write`.")
        return 1
    committed = MANIFEST.read_text(encoding="utf-8")
    if committed != rendered:
        print(f"{MANIFEST.relative_to(ROOT)} is stale; regenerate with "
              f"`python scripts/prereg_manifest.py --write`.")
        return 1

    print(f"Pre-registration manifest verified: {n_verified} locked files re-hash against committed bytes "
          f"({n_superseded} superseded phase-0 seal disclosed); {len(ledger)} Table 3 pre-registrations "
          f"cited and re-hashed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
