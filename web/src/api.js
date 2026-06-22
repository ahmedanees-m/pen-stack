// Typed client over the PEN-STACK web gateway. The gateway mounts the v6.1 engine surface under /api and the
// grounded co-scientist at /chat. Every number these endpoints return is computed by the engine, the UI only
// renders. Base URL is "" (same origin: the gateway serves the built frontend) unless VITE_API_BASE overrides.
const BASE = (import.meta.env.VITE_API_BASE || "").replace(/\/$/, "");

async function req(path, { method = "GET", body, signal } = {}) {
  const res = await fetch(BASE + path, {
    method,
    headers: body ? { "Content-Type": "application/json" } : undefined,
    body: body ? JSON.stringify(body) : undefined,
    signal,
  });
  const text = await res.text();
  let data;
  try { data = text ? JSON.parse(text) : null; } catch { data = { raw: text }; }
  if (!res.ok) {
    const detail = (data && (data.detail || data.error)) || res.statusText;
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  return data;
}

export const api = {
  health: () => req("/health"),

  // v6.1 AI surface (mounted at /api)
  capabilities: () => req("/api/capabilities"),
  scope: () => req("/api/scope"),
  verify: (design) => req("/api/verify", { method: "POST", body: design }),
  verifyProof: (design) => req("/api/verify/proof", { method: "POST", body: design }),
  safety: (design) => req("/api/safety", { method: "POST", body: design }),
  immune: (design) => req("/api/immune", { method: "POST", body: design }),
  generate: (reqbody) => req("/api/generate", { method: "POST", body: reqbody }),
  predict: (reqbody) => req("/api/predict", { method: "POST", body: reqbody }),
  suggest: (reqbody) => req("/api/suggest", { method: "POST", body: reqbody }),
  session: (reqbody) => req("/api/session", { method: "POST", body: reqbody }),

  // v6.10 off-target nomination
  offtarget: (reqbody) => req("/api/offtarget", { method: "POST", body: reqbody }),
  offtargetAssay: (family) => req(`/api/offtarget/assay?${new URLSearchParams({ writer_family: family })}`),

  // v6.13 oracle mesh: status + published reliability, and protein-ligand binding affinity (Boltz-2)
  oracles: (probe = false) => req(`/api/oracles${probe ? "?probe=true" : ""}`),
  oracleAffinity: (reqbody) => req("/api/oracle/affinity", { method: "POST", body: reqbody }),

  // atlas + site finder
  atlas: (family, limit = 200) =>
    req(`/api/atlas?${new URLSearchParams({ ...(family ? { family } : {}), limit })}`),
  atlasCoverage: () => req("/api/atlas/coverage"),
  writable: (gene, ct = "k562", top = 20) =>
    req(`/api/writable?${new URLSearchParams({ gene, ct, top })}`),
  plan: (gene, intent, cargo_bp = 2000, ct = "k562", k = 6) =>
    req(`/api/plan?${new URLSearchParams({ gene, intent, cargo_bp, ct, k })}`),

  // challenge
  challengeTasks: (round = "2026R1") => req(`/api/challenge/tasks?round_id=${round}`),
  challengeLeaderboard: (round = "2026R1") => req(`/api/challenge/leaderboard?round_id=${round}`),

  // the grounded co-scientist chat
  chat: (message, history = [], allow_llm = true) =>
    req("/chat", { method: "POST", body: { message, history, allow_llm } }),
};

// Streamed chat (SSE). onToken(text) per word; resolves with the final {tool_results, backend, grounded}.
export async function chatStream(message, history, { onToken, allow_llm = true, signal } = {}) {
  const res = await fetch(BASE + "/chat/stream", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, history, allow_llm }),
    signal,
  });
  if (!res.ok || !res.body) throw new Error("stream failed: " + res.status);
  const reader = res.body.getReader();
  const dec = new TextDecoder();
  let buf = "";
  let done_payload = null;
  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    buf += dec.decode(value, { stream: true });
    const events = buf.split("\n\n");
    buf = events.pop() || "";
    for (const ev of events) {
      const isDone = ev.includes("event: done");
      const line = ev.split("\n").find((l) => l.startsWith("data: "));
      if (!line) continue;
      const payload = JSON.parse(line.slice(6));
      if (isDone) done_payload = payload;
      else if (payload.token) onToken?.(payload.token);
    }
  }
  return done_payload || {};
}
