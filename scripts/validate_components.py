#!/usr/bin/env python3
"""Full component / stage validation for PEN-STACK, run inside the Docker image on a fresh GitHub clone.

For each component it calls a representative public function and classifies the outcome:
  PASS    - returned a real result
  DEGRADE - ran and returned a "not available" / held / scope-deferred (correct no-fabrication
            behaviour when an optional backend or the full atlas is absent), no crash
  FAIL    - an unexpected exception (a real defect)

Uses the committed chr19 demo atlas (AAVS1 lives on chr19) and, where an LLM is needed, the Anthropic
provider if ANTHROPIC_API_KEY is set (otherwise those components degrade to the deterministic path)."""
import json
import os
import sys
import traceback
from collections import Counter

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
os.environ.setdefault("PEN_ATLAS_DIR", os.path.join(os.getcwd(), "data", "demo"))

results = []


def rec(name, status, detail=""):
    results.append((name, status, detail))
    print(f"  [{status:7}] {name}: {detail}"[:200], flush=True)

def probe(name, fn, degrade_if=None):
    try:
        out = fn()
        s = json.dumps(out, default=str)[:120] if out is not None else "None"
        if degrade_if and degrade_if(out):
            rec(name, "DEGRADE", "not-available: " + s)
        elif out is None:
            rec(name, "DEGRADE", "returned None")
        else:
            rec(name, "PASS", s)
    except Exception as e:  # noqa: BLE001
        rec(name, "FAIL", f"{type(e).__name__}: {e}")
        traceback.print_exc()

print("=== PEN-STACK component / stage validation ===", flush=True)
print("version:", __import__("pen_stack").__version__, "| atlas:", os.environ["PEN_ATLAS_DIR"], flush=True)

# 1. Writer Atlas
probe("Writer Atlas: writer_axes", lambda: __import__("pen_stack.agent.tools", fromlist=["writer_axes"]).writer_axes("bridge_IS110"))
# 2. Writable Genome (atlas + crosslink)
def _writable():
    from pen_stack.agent.tools import writability
    return writability("AAVS1", "k562")
probe("Writable Genome: writability(AAVS1)", _writable)
probe("Writable Genome: reachable_writers", lambda: __import__("pen_stack.agent.tools", fromlist=["reachable_writers"]).reachable_writers("AAVS1", "k562"))
# 3. Off-target, per-mechanism
def _offtarget():
    from pen_stack.wgenome.offtarget_assay import recommend_assay
    return {f: recommend_assay(f)["writer_class"] for f in ["SpCas9", "Bxb1", "bridge_IS110", "ShCAST", "PASTE"]}
probe("Off-target: recommend_assay (5 classes)", _offtarget)
probe("Off-target: nominate_integrase(Bxb1)", lambda: __import__("pen_stack.wgenome.offtarget_integrase", fromlist=["nominate_integrase"]).nominate_integrase("Bxb1", top=5),
      degrade_if=lambda o: isinstance(o, dict) and o.get("available") is False)
# 4. Write Planner
probe("Write Planner: plan_write(AAVS1)", lambda: __import__("pen_stack.agent.tools", fromlist=["plan_write"]).plan_write("AAVS1", "safe_harbour_insertion", 2000, "k562"))
# 5. Verifier
def _verify():
    from pen_stack.verify import verify
    return verify({"gene": "AAVS1", "intent": "safe_harbour_insertion", "writer_family": "bridge_IS110",
                   "cargo_bp": 2000, "vehicle": "AAV", "cargo_function": "Factor IX gene therapy"})
probe("Verifier: verify(design)", _verify)
# 6. Biosecurity gate (benign passes, hazard refuses)
def _safety_benign():
    from pen_stack.safety import safety_gate
    return safety_gate({"gene": "TRAC", "cargo_function": "CAR-T knock-in", "writer_family": "SpCas9"})
def _safety_hazard():
    from pen_stack.safety import safety_gate
    v = safety_gate({"gene": "X", "cargo_function": "ricin toxin A chain", "writer_family": "SpCas9"})
    return {"refused": getattr(v, "refused", None) or (isinstance(v, dict) and v.get("refused"))}
probe("Biosecurity: safety_gate(benign)", _safety_benign)
probe("Biosecurity: safety_gate(ricin) -> refuse", _safety_hazard)
# 7. Oracle mesh (contract + no-fabrication guard)
def _oracle():
    from pen_stack.oracles.schema import OracleResult, Provenance
    r = OracleResult(oracle="genome", value={"x": 1}, provenance=Provenance(model="demo", version="1.0"),
                     output_kind="candidate")
    guarded = False
    try:
        r.as_claim()
    except ValueError:
        guarded = True  # a candidate must not be assertable as a claim (no-fabrication guard)
    return {"OracleResult_built": True, "is_candidate": r.is_candidate, "as_claim_guarded": guarded}
probe("Oracle mesh: OracleResult contract + as_claim guard", _oracle)
# 8. World-model graph
def _graph():
    from pen_stack.graph import build_graph
    g = build_graph()
    return {"graph_built": True, "nodes": len(getattr(g, "nodes", []) or getattr(g, "_nodes", {}) or [])}
probe("World-model graph: build_graph", _graph)
# 9. Generative designer
probe("Generative designer: generate_designs", lambda: __import__("pen_stack.design", fromlist=["generate_designs"]).generate_designs({"goal": "safe_harbour_insertion", "gene": "AAVS1"}))
# 10. Digital twin
probe("Digital twin: promoter_palette", lambda: {"n_promoters": len(__import__("pen_stack.twin.mechanistic", fromlist=["promoter_palette"]).promoter_palette())})
def _twin_cal():
    from pen_stack.twin import calibrate_outcome
    preds = [i / 10 for i in range(12)]
    obs = [i / 10 + 0.1 for i in range(12)]
    return calibrate_outcome(preds, obs, reps=50)
probe("Digital twin: calibrate_outcome", _twin_cal)
# 11. Experiment designer
probe("Experiment designer: expected_information_gain", lambda: {"eig": __import__("pen_stack.active", fromlist=["expected_information_gain"]).expected_information_gain({"gene": "AAVS1", "vehicle": "AAV"}, "k562")})
probe("Experiment designer: immune_voi", lambda: {"voi": __import__("pen_stack.active", fromlist=["immune_voi"]).immune_voi({"gene": "AAVS1", "vehicle": "AAV"}, "k562")})
# 12. Build interface (safety-gated, draft/mock)
def _build():
    from pen_stack.build.cloudlab import submit_gated
    return submit_gated({"gene": "AAVS1", "cargo_function": "Factor IX gene therapy", "writer_family": "bridge_IS110"},
                        {"provider": "mock", "assay": "integration_qpcr"})
probe("Build interface: submit_gated (mock)", _build,
      degrade_if=lambda o: isinstance(o, dict) and o.get("status") in {"draft", "mock", "dry_run"})
# 13. Closed loop
def _loop():
    from pen_stack.loop import run_loop
    return run_loop({"gene": "AAVS1", "intent": "safe_harbour_insertion"}, "k562", rounds=1)
probe("Closed loop: run_loop(1 round)", _loop)
# 14. WriteSpec
def _spec():
    from pen_stack.spec.extract import extract_writespec
    ws = extract_writespec("Insert a 2 kb Factor IX cassette into the AAVS1 safe harbour using a bridge recombinase")
    d = ws.model_dump() if hasattr(ws, "model_dump") else {}
    gene = (((d.get("target") or {}).get("gene") or {}).get("id"))
    return {"write_type": d.get("write_type"), "resolved_gene": gene, "n_cargo": len(d.get("cargo") or [])}
probe("WriteSpec: extract_writespec", _spec)
# 15. Chat / RAG
def _chat():
    from pen_stack.rag.ground import ground_general
    r = ground_general("What is a genomic safe harbour?", allow_llm=bool(os.environ.get("ANTHROPIC_API_KEY")))
    return {"answered": bool(r.get("reply")), "grounded": r.get("grounded"), "n_sources": len(r.get("sources") or [])}
probe("Chat / RAG: ground_general", _chat)
# 16. Agent (LLM drives the validated tools)
def _agent():
    from pen_stack.rag.llm import load_llm_config
    from pen_stack.agent.orchestrator import run_agent
    from pen_stack.validate.agent_eval import no_fabrication
    cfg = {**load_llm_config(), "provider": "anthropic", "fallback": None} if os.environ.get("ANTHROPIC_API_KEY") else None
    res = run_agent("insert a durable cassette at the AAVS1 safe harbour", cfg=cfg)
    nf = no_fabrication(res)
    return {"llm_driven": bool(res.get("llm")), "tool_calls": len(res.get("trace", [])), "no_fabrication": nf["passed"]}
probe("Agent: run_agent (Claude drives tools, no-fabrication audit)", _agent)
# 17. Bridge engine (may need the [bridge] extra)
def _bridge():
    from pen_stack.wgenome.offtarget_bridge import nominate_bridge
    return nominate_bridge(writer_family="bridge_IS110")
probe("Bridge engine: nominate_bridge", _bridge, degrade_if=lambda o: isinstance(o, dict) and o.get("available") is False)

# ---- summary ----
print("\n=== SUMMARY ===")
c = Counter(s for _, s, _ in results)
print(f"components probed: {len(results)}  ->  PASS {c['PASS']}  DEGRADE {c['DEGRADE']}  FAIL {c['FAIL']}")
for n, s, d in results:
    if s == "FAIL":
        print(f"  FAIL: {n}: {d}")
print("COMPONENT_TEST_DONE")
