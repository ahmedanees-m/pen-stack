"""pen_stack.build, the digital→physical bridge (v5.11).

Make designs executable and results ingestible, loop-ready and lab-optional, with safety wired in at the point
where software reaches for the physical world: a cleared, legal design becomes a runnable protocol DRAFT
carrying its v5.6 immune-risk profile (refused outright if the v5.7 safety gate flags it); a typed ingestion API
returns experimental results as candidate evidence admitted only through the v4.5 world-model gate; and a
simulated lab runs the whole loop before any hardware exists. PEN-STACK emits protocols and ingests results, it
does NOT run experiments.
"""
from __future__ import annotations

from pen_stack.build.ingest import ResultSchemaError, ingest_result
from pen_stack.build.protocol import ProtocolExportError, export_protocol
from pen_stack.build.simlab import run_simulated

__all__ = ["export_protocol", "ProtocolExportError", "ingest_result", "ResultSchemaError", "run_simulated"]
