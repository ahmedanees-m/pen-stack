#!/usr/bin/env bash
# ---------------------------------------------------------------------------------------------------
# fetch_artifacts.sh - one-command fetch of the PEN-STACK released atlas + model artifacts (GigaScience
# reproducibility). Downloads the OPEN "Writable Genome" data release from Zenodo into the two locations
# the package + benchmarks read from:
#
#     data/out/   <- atlas_tracks/*  (atlas_<ct>.parquet, *_writability/_safety/_p_durable.bw, *_top5000.bed,
#                                     gene_coords.parquet)   [resolved by pen_stack.atlas.crosslink + the UI]
#     models/     <- models/*        (durability.pkl, safety_<ct>.pkl, position_effect*.pkl, capsid_fitness.pkl)
#
# Idempotent: already-downloaded files (matching size) and already-installed files (identical bytes) are
# skipped. Verifies integrity with `sha256sum -c` against the deposit's own SHA256SUMS manifest.
#
# Defaults to the v0.1.0 version DOI so a fresh clone fetches the exact data v0.1.0 was scored on.
# Export ZENODO_DOI to pull a different release; the concept DOI 10.5281/zenodo.21787136 always
# resolves to the newest one.
#
# NOTE (licensed sources): this fetches the OPEN release only. License-restricted enrichment sources
# (COSMIC Cancer Gene Census, OncoKB) are NEVER redistributed here - see scripts/fetch_licensed_sources.py,
# which documents your own registered download under your own license.
#
#     bash scripts/fetch_artifacts.sh              # fetch + verify + install into data/out/ and models/
#     ZENODO_DOI=10.5281/zenodo.21787137 bash scripts/fetch_artifacts.sh   # a different release
#     PEN_ATLAS_DIR=/some/other/dir bash scripts/fetch_artifacts.sh   # override the atlas destination
# ---------------------------------------------------------------------------------------------------
set -euo pipefail

# --- 0. configuration ------------------------------------------------------------------------------
# The version DOI of the Zenodo deposit, pinned to v0.1.0 for reproducibility.
ZENODO_DOI="${ZENODO_DOI:-10.5281/zenodo.21787137}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Atlas destination: PEN_ATLAS_DIR (also honoured by the package/UI) wins; default data/out/.
DATA_OUT="${PEN_ATLAS_DIR:-${REPO_ROOT}/data/out}"
MODELS_DIR="${REPO_ROOT}/models"
STAGING="${REPO_ROOT}/data/zenodo_download"   # deposit-native layout kept here for checksum verification

log()  { printf '\033[1;34m[fetch]\033[0m %s\n' "$*"; }
ok()   { printf '\033[1;32m[ ok  ]\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m[warn]\033[0m %s\n' "$*" >&2; }
die()  { printf '\033[1;31m[fail]\033[0m %s\n' "$*" >&2; exit 1; }

# --- 1. detect required tooling --------------------------------------------------------------------
if command -v curl >/dev/null 2>&1; then
  DL() { curl -fSL --retry 3 --retry-delay 2 -o "$2" "$1"; }          # DL <url> <out>
  DLQ() { curl -fsSL "$1"; }                                          # DLQ <url> -> stdout
elif command -v wget >/dev/null 2>&1; then
  DL() { wget -q --tries=3 -O "$2" "$1"; }
  DLQ() { wget -qO- "$1"; }
else
  die "need curl or wget on PATH"
fi

if command -v sha256sum >/dev/null 2>&1; then
  HAVE_SHA=1
  SHA_C() { sha256sum -c "$1"; }                                      # verify a checksums file (cwd-relative)
  SHA_1() { sha256sum "$1" | awk '{print $1}'; }                      # print sha256 of one file
elif command -v shasum >/dev/null 2>&1; then
  HAVE_SHA=1
  SHA_C() { shasum -a 256 -c "$1"; }
  SHA_1() { shasum -a 256 "$1" | awk '{print $1}'; }
else
  HAVE_SHA=0
  warn "no sha256sum/shasum found - integrity verification will be SKIPPED"
fi

PYTHON="${PYTHON:-}"
if [ -z "${PYTHON}" ]; then
  if command -v python3 >/dev/null 2>&1; then PYTHON=python3
  elif command -v python >/dev/null 2>&1; then PYTHON=python
  else die "need python3/python on PATH (to parse the Zenodo record listing)"; fi
fi

# --- 2. resolve the Zenodo record + enumerate its files --------------------------------------------
RECORD_ID="${ZENODO_DOI##*.}"          # 10.5281/zenodo.1234567 -> 1234567
case "${RECORD_ID}" in
  ''|*[!0-9]*) die "could not parse a numeric record id from ZENODO_DOI='${ZENODO_DOI}'";;
esac
API="https://zenodo.org/api/records/${RECORD_ID}"

mkdir -p "${STAGING}" "${DATA_OUT}" "${MODELS_DIR}"
log "Zenodo record ${RECORD_ID} (DOI ${ZENODO_DOI})"
log "querying ${API}"
DLQ "${API}" > "${STAGING}/_record.json" || die "could not reach the Zenodo API for record ${RECORD_ID}"

# Emit one "<key>\t<size>" line per file. Tolerant of both the legacy and InvenioRDM JSON shapes.
"${PYTHON}" - "${STAGING}/_record.json" > "${STAGING}/_files.tsv" <<'PY'
import json, sys
doc = json.load(open(sys.argv[1], encoding="utf-8"))
files = doc.get("files")
if isinstance(files, dict):          # InvenioRDM: {"entries": {name: {...}}} or {"entries": [...]}
    entries = files.get("entries", files)
    files = list(entries.values()) if isinstance(entries, dict) else entries
files = files or []
for f in files:
    key = f.get("key") or f.get("filename") or f.get("name")
    size = f.get("size") or f.get("filesize") or 0
    if key:
        print(f"{key}\t{size}")
PY

[ -s "${STAGING}/_files.tsv" ] || die "the Zenodo record lists no files (record ${RECORD_ID})"
N_FILES=$(wc -l < "${STAGING}/_files.tsv" | tr -d ' ')
log "record advertises ${N_FILES} file(s); downloading into ${STAGING}"

# --- 3. download each file (idempotent: skip when present with the advertised size) ----------------
while IFS=$'\t' read -r KEY SIZE; do
  [ -n "${KEY}" ] || continue
  OUT="${STAGING}/${KEY}"
  mkdir -p "$(dirname "${OUT}")"
  if [ -f "${OUT}" ] && [ "${SIZE}" != "0" ]; then
    HAVE=$(wc -c < "${OUT}" | tr -d ' ')
    if [ "${HAVE}" = "${SIZE}" ]; then ok "cached  ${KEY} (${SIZE} bytes)"; continue; fi
  fi
  # Canonical, API-shape-independent Zenodo download URL.
  URL="https://zenodo.org/records/${RECORD_ID}/files/${KEY}?download=1"
  log "get     ${KEY}"
  DL "${URL}" "${OUT}" || die "download failed: ${KEY}"
done < "${STAGING}/_files.tsv"

# --- 4. if the deposit was uploaded as a single archive, unpack it (deposit-native layout) ---------
shopt -s nullglob
for arc in "${STAGING}"/*.zip "${STAGING}"/*.tar.gz "${STAGING}"/*.tgz; do
  log "extract ${arc##*/}"
  case "${arc}" in
    *.zip)            ( cd "${STAGING}" && unzip -o -q "${arc}" ) ;;
    *.tar.gz|*.tgz)   tar -xzf "${arc}" -C "${STAGING}" ;;
  esac
done
shopt -u nullglob

# --- 5. verify integrity ---------------------------------------------------------------------------
CHECKSUMS="$(find "${STAGING}" \( -name 'SHA256SUMS' -o -name 'checksums.sha256' \) -type f 2>/dev/null | head -n1 || true)"
if [ "${HAVE_SHA}" = "0" ]; then
  warn "no checksum tool - skipping integrity verification"
elif [ -n "${CHECKSUMS}" ]; then
  CDIR="$(dirname "${CHECKSUMS}")"
  log "verifying against $(basename "${CHECKSUMS}") (${CDIR})"
  if ( cd "${CDIR}" && SHA_C "$(basename "${CHECKSUMS}")" ) >/dev/null 2>&1; then
    ok "sha256 verified (deposit layout)"
  else
    # Layout differs from the checksums manifest (e.g. flat upload) - verify per basename instead.
    warn "layout does not match checksums manifest paths - verifying by basename"
    BAD=0
    while read -r WANT RELPATH; do
      [ -n "${WANT:-}" ] || continue
      BASE="$(basename "${RELPATH}")"
      FOUND="$(find "${STAGING}" -name "${BASE}" -type f | head -n1 || true)"
      [ -n "${FOUND}" ] || { warn "missing ${BASE}"; BAD=1; continue; }
      GOT="$(SHA_1 "${FOUND}")" || { warn "cannot hash ${BASE}"; BAD=1; continue; }
      if [ "${GOT}" != "${WANT}" ]; then warn "checksum mismatch ${BASE}"; BAD=1; fi
    done < "${CHECKSUMS}"
    [ "${BAD}" = "0" ] && ok "sha256 verified (by basename)" || die "integrity verification FAILED"
  fi
else
  warn "no SHA256SUMS/checksums.sha256 in the deposit - skipping integrity verification"
fi

# --- 6. install into data/out/ and models/ (idempotent copy) ---------------------------------------
# Route by basename so this works whether the deposit is flat or keeps atlas_tracks/ + models/ subdirs.
install_one() {  # install_one <src> <dest_dir>
  local src="$1" dest_dir="$2" dst
  dst="${dest_dir}/$(basename "${src}")"
  mkdir -p "${dest_dir}"
  if [ -f "${dst}" ] && cmp -s "${src}" "${dst}"; then
    ok "in place ${dst#${REPO_ROOT}/}"
  else
    cp -f "${src}" "${dst}"
    ok "install  ${dst#${REPO_ROOT}/}"
  fi
}

log "installing atlas tracks -> ${DATA_OUT#${REPO_ROOT}/}"
N_ATLAS=0
while IFS= read -r src; do
  install_one "${src}" "${DATA_OUT}"; N_ATLAS=$((N_ATLAS + 1))
done < <(find "${STAGING}" -type f \( -name 'atlas_*.parquet' -o -name 'atlas_*.bw' -o -name 'atlas_*.bed' \
                                       -o -name 'gene_coords.parquet' \) | sort)

log "installing models -> ${MODELS_DIR#${REPO_ROOT}/}"
N_MODELS=0
while IFS= read -r src; do
  install_one "${src}" "${MODELS_DIR}"; N_MODELS=$((N_MODELS + 1))
done < <(find "${STAGING}" -type f \( -name 'durability.pkl' -o -name 'safety_*.pkl' -o -name 'position_effect.pkl' -o -name 'position_effect_human_k562.pkl' -o -name 'capsid_fitness.pkl' \) | sort)

# --- 7. summary ------------------------------------------------------------------------------------
echo
ok "done: ${N_ATLAS} atlas track file(s) -> ${DATA_OUT}"
ok "      ${N_MODELS} model file(s) -> ${MODELS_DIR}"
if [ "${N_ATLAS}" = "0" ]; then
  warn "no atlas tracks were installed - check the deposit contents in ${STAGING}"
fi
cat <<EOF

Next:
  make repro                 # run the headline benchmarks against the fetched atlas
  python -c "from pen_stack.atlas import crosslink; print(crosslink.writability_path('k562'))"

The full deposit (supervision_features/, validation/, writer_kb/) is staged under:
  ${STAGING}
License-restricted enrichment (COSMIC/OncoKB) is NOT here - see scripts/fetch_licensed_sources.py.
EOF
