# Oracle cache (v4.0, WS-O)

Version-pinned, deterministic cache for the L1 oracle mesh. Each entry is a JSON file named by the
`cache_key` (sha256 over the oracle family, the pinned model+version, and canonicalised inputs, see
`pen_stack/oracles/cache.py`). Committed entries let the substrate **replay heavy-oracle values offline**
(the v4.0 compute policy: core stays runnable from cache when AF3/Evo2/ESM3/… backends are absent).

When a real oracle backend runs (on the VM / a hosted API), its `OracleResult.value` and `native_uncertainty`
are written here keyed on the call; subsequent calls replay from cache (`cached=True`, `source="cache"`).
Adapters that find neither a backend nor a cache entry return a **deferred** result (`available=False`), they
never fabricate a value.
