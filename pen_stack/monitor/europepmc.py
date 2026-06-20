"""Europe PMC client for PEN-MONITOR (Phase 2, Step 2.7).

Europe PMC is the right primary source: open REST API, full-text + preprints, no licence friction.
This module only *fetches* - triage + queueing live in triage.py / run.py.
"""
from __future__ import annotations

import time
import urllib.parse
import urllib.request
from io import BytesIO
import json

EPMC = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"


def search(query: str, since_date: str | None = None, page_size: int = 100,
           timeout: int = 30, retries: int = 3) -> list[dict]:
    """Search Europe PMC. ``since_date`` (YYYY-MM-DD) filters on first publication date."""
    q = query if not since_date else f"{query} AND FIRST_PDATE:[{since_date} TO *]"
    params = {"query": q, "format": "json", "pageSize": page_size, "resultType": "core"}
    url = EPMC + "?" + urllib.parse.urlencode(params)
    last = None
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(url, timeout=timeout) as r:
                data = json.load(BytesIO(r.read()))
            return data.get("resultList", {}).get("result", [])
        except Exception as e: # noqa: BLE001 - network best-effort
            last = e
            time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"Europe PMC search failed for {query!r}: {last}")
