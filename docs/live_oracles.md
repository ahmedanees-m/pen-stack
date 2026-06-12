# Live Oracles (v6.4)

PEN-STACK's foundation-model oracles can **actually execute** — not just defer. v6.4 wires the live paths and
adds an honest **execution + latency** surface so the assistant tells you the cost *before* it runs anything.

## The no-fabrication invariant is unchanged

Live or deferred, the rule holds: a generative output is a **candidate** (`as_claim()` raises), an OOD input is
flagged `extrapolating`, and when a backend is down the adapter **defers** — it never fabricates a number.
Turning a model "on" is opt-in via **`PEN_STACK_ORACLE_NET=1`**; with the flag unset (CI / offline) every oracle
behaves exactly as before.

## What runs where, and how long

| Oracle | Execution | Latency | How to enable |
|---|---|---|---|
| **ViennaRNA** | in-process | **instant** (<1 s) | always on |
| **AlphaGenome** | hosted API (free) | **seconds** (~2–10 s) | `configs/alphagenome_api_key.txt` + `PEN_STACK_ORACLE_NET=1` |
| **Evo2-40B** | hosted API (NVIDIA) | **seconds** (~1–3 s) | `configs/nvidia_api_key.txt` + `PEN_STACK_ORACLE_NET=1` |
| **ProteinMPNN** | local GPU server :9011 | **seconds** (~1–9 s) | start the model server + `PEN_STACK_ORACLE_NET=1` |
| **ESM3-open 1.4B** | local GPU server :9012 | **seconds** (~1–2 s warm) | start the model server + flag |
| **RFdiffusion** | local GPU server :9013 | **slow** (~1–2 min) | start the model server + flag *(warn the user)* |
| Arc STATE / scGPT | deferred | long_job | perturbation **outcome** needs the State-Transition model + a reference scRNA pipeline; honestly deferred |
| AlphaFold3 · Boltz-2 · Chai-1 · Protenix | **HELD** (cloud A100) | long_job | run **separately** on a rented A100/H100; not active now |

Query the live status any time: `GET /oracles` (add `?probe=true` to ping the local servers), or
`pen_stack.oracles.status.summary()`.

## Starting the local GPU model servers (on demand)

The local models run as small FastAPI services on the VM GPU — start only what you need:

```bash
# build bases once (penstack:phase1.5 already on the VM; rfdiffusion:base from the RFdiffusion repo)
docker compose -f docker-compose.models.yml up -d proteinmpnn esm3      # the fast ones
docker compose -f docker-compose.models.yml up -d rfdiffusion           # the slow one (~1–2 min/run)
```

Then run the engine with the live flag + keys:

```bash
PEN_STACK_ORACLE_NET=1 \
NVIDIA_API_KEY=$(cat configs/nvidia_api_key.txt) \
ALPHAGENOME_API_KEY=$(cat configs/alphagenome_api_key.txt) \
uvicorn pen_stack.web.server:app --port 8000
```

## Latency policy ("tell the user up front")

- **instant / seconds** → answered inline.
- **slow** (RFdiffusion) → *"Running RFdiffusion on the GPU, ~1–2 min…"* then the result.
- **long_job** (AF3 / Boltz / Chai / Protenix) → *"This needs a cloud A100 and takes minutes — run it separately"*;
  never silently blocks the chat.

The cloud-A100 structure models are **held on purpose** (see the v6.4 changelog): they can be run via these same
oracle adapters by pointing them at a cloud GPU, just not on the 16 GB VM and not in the request path.
