// The front door: a grounded co-scientist chat. The LLM narrates and routes; the ENGINE sources every number,
// and each answer carries its dossier, the verdict, safety, the per-axis immune profile, and the scope ledger,
// rendered through the provenance-UX components. With LLM narration off, the deterministic narrator answers instead.
import React, { useEffect, useRef, useState } from "react";
import { api, chatStream } from "../api.js";
import { Card, Button, Spinner } from "../components/ui.jsx";
import VerdictCard from "../components/VerdictCard.jsx";
import SafetyBadge from "../components/SafetyBadge.jsx";
import ImmuneProfileCard from "../components/ImmuneProfileCard.jsx";
import ScopeLedger from "../components/ScopeLedger.jsx";

const EXAMPLES = [
  "Durably express Factor IX in adult liver using AAV, 4.5 kb cargo",
  "Knock in a CAR into the TRAC locus of a CD8 T cell",
  "Insert a 6 kb cassette at AAVS1 with a single AAV, is that legal?",
  "Will this LNP-mRNA edit cause an innate immune response?",
  "What can you NOT tell me about in-vivo immunogenicity?",
];

export default function CoScientist({ onBackend, allowLlm }) {
  const [msgs, setMsgs] = useState([]); // {role, content, dossier?, backend?}
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const endRef = useRef(null);

  useEffect(() => { endRef.current?.scrollIntoView({ behavior: "smooth" }); }, [msgs, busy]);

  async function send(text) {
    const q = (text ?? input).trim();
    if (!q || busy) return;
    setInput("");
    // P-WS3: carry each turn's lane + provenance so a follow-up resolves against the prior answer's grounding.
    const history = msgs.map((m) => ({ role: m.role, content: m.content, mode: m.mode, provenance: m.provenance }));
    setMsgs((m) => [...m, { role: "user", content: q }, { role: "assistant", content: "", streaming: true }]);
    setBusy(true);
    try {
      let acc = "";
      const done = await chatStream(q, history, {
        allow_llm: allowLlm,
        onToken: (t) => {
          acc += t;
          setMsgs((m) => { const c = [...m]; c[c.length - 1] = { role: "assistant", content: acc, streaming: true }; return c; });
        },
      });
      onBackend?.(done.backend);
      setMsgs((m) => { const c = [...m]; c[c.length - 1] = { role: "assistant", content: acc, dossier: done.tool_results || null, backend: done.backend, mode: done.mode, provenance: done.provenance, angles: done.angles, sources: done.sources, status: done.status }; return c; });
    } catch (e) {
      // network/stream failure → fall back to the non-streamed grounded endpoint
      try {
        const r = await api.chat(q, history, allowLlm);
        onBackend?.(r.backend);
        setMsgs((m) => { const c = [...m]; c[c.length - 1] = { role: "assistant", content: r.reply, dossier: r.tool_results, backend: r.backend, mode: r.mode, provenance: r.provenance, angles: r.angles }; return c; });
      } catch (e2) {
        setMsgs((m) => { const c = [...m]; c[c.length - 1] = { role: "assistant", content: "", error: String(e2.message || e2) }; return c; });
      }
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_360px]">
      <div className="flex min-h-[70vh] flex-col">
        {msgs.length === 0 ? (
          <Welcome onPick={send} />
        ) : (
          <div className="flex-1 space-y-4">
            {msgs.map((m, i) => <Message key={i} m={m} onPick={send} />)}
            <div ref={endRef} />
          </div>
        )}

        <div className="sticky bottom-0 mt-4 bg-gradient-to-t from-ink-950 to-transparent pt-3">
          <div className="flex items-end gap-2">
            <textarea
              className="input min-h-[46px] resize-none"
              rows={1}
              placeholder="Ask a genome-writing question… (Enter to send, Shift+Enter for newline)"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); } }}
            />
            <Button onClick={() => send()} disabled={busy || !input.trim()}>Send</Button>
          </div>
          <p className="mt-1.5 text-[11px] text-fg-faint">
            Genome-writing questions are answered by the engine (every number tool-sourced, guarded). General
            questions are answered from a cited literature corpus, or the assistant abstains, never an unsourced
            guess. Every answer carries its lane and provenance.
          </p>
        </div>
      </div>

      {/* Latest dossier rail */}
      <div className="hidden lg:block">
        <div className="sticky top-20 space-y-3">
          <LatestDossier msgs={msgs} busy={busy} />
        </div>
      </div>
    </div>
  );
}

function Welcome({ onPick }) {
  return (
    <Card className="bg-ink-850/60">
      <h2 className="text-lg font-semibold">Ask in plain language.</h2>
      <p className="mt-1 text-sm text-fg-dim">
        Describe a genome-writing goal. The co-scientist parses it, runs the verifier, the Guardian, and the immune
        profiler, and explains the result, grounding every number in the engine and listing what it cannot tell you.
      </p>
      <div className="mt-4 flex flex-wrap gap-2">
        {EXAMPLES.map((ex) => (
          <button key={ex} onClick={() => onPick(ex)}
            className="rounded-lg border border-line bg-ink-900 px-3 py-1.5 text-left text-xs text-fg-dim hover:border-brand/40 hover:text-fg">
            {ex}
          </button>
        ))}
      </div>
    </Card>
  );
}

function Message({ m, onPick }) {
  if (m.role === "user") {
    return (
      <div className="flex justify-end">
        <div className="max-w-[85%] rounded-2xl rounded-br-sm border border-brand/25 bg-brand/10 px-4 py-2.5 text-sm">{m.content}</div>
      </div>
    );
  }
  const cited = m.provenance === "literature-cited";
  const abstained = m.provenance === "abstained";
  const safety = m.mode === "safety";
  const tint = safety ? "border-bad/30 bg-bad/5" : cited ? "border-brand/25 bg-brand/5"
    : abstained ? "border-warn/30 bg-warn/5" : "border-line bg-ink-850";
  const footer = safety ? "declined by the biosecurity screen" : cited ? "from the cited literature corpus"
    : abstained ? "abstained, no grounded source" : "numbers from the engine";
  return (
    <div className="flex justify-start">
      <div className="max-w-[92%] space-y-3">
        <div className={`rounded-2xl rounded-bl-sm border px-4 py-3 text-sm leading-relaxed ${tint}`}>
          {m.provenance && !m.streaming && <ProvenanceBadge mode={m.mode} provenance={m.provenance} />}
          {m.error ? <span className="text-bad">Engine error: {m.error}</span> : <Markdownish text={m.content} />}
          {m.streaming && <span className="ml-1 inline-block h-3 w-1.5 animate-pulse bg-brand align-middle" />}
          {!m.streaming && <SourceChips sources={m.sources} />}
          {m.angles?.length > 0 && <AnglePointers angles={m.angles} onPick={onPick} />}
          {m.backend && (
            <div className="mt-2 text-[10.5px] text-fg-faint">
              {footer} · narrated by <span className="font-mono">{m.backend}</span>
            </div>
          )}
        </div>
        {m.dossier && <InlineDossier d={m.dossier} />}
      </div>
    </div>
  );
}

const MODE_LABEL = { design: "grounded design", explain: "metric guide", meta: "about the engine" };
// PEN-CHAT v7.1: every lane carries its own provenance, including the new retrieval-grounded / abstained / refused
// states. The colour encodes the grounding posture: green = engine-grounded, cyan = literature-cited, amber =
// abstained (no grounded source), red = declined by the biosecurity screen.
function provInfo(mode, provenance) {
  if (mode === "safety") return { label: "Declined · biosecurity screen", color: "var(--bad)" };
  if (provenance === "pen-stack") return { label: "PEN-STACK · " + (MODE_LABEL[mode] || "grounded"), color: "var(--ok)" };
  if (provenance === "literature-cited") return { label: "Literature-cited (corpus)", color: "var(--brand)" };
  if (provenance === "abstained") return { label: "Abstained · no grounded source", color: "var(--warn)" };
  return { label: "PEN-STACK", color: "var(--ok)" };
}
function ProvenanceBadge({ mode, provenance }) {
  const { label, color } = provInfo(mode, provenance);
  return (
    <div className="mb-2 inline-flex items-center gap-1.5 rounded-md border px-2 py-0.5 text-[10.5px] font-medium"
         style={{ borderColor: color + "55", color }}>{label}</div>
  );
}
function SourceChips({ sources }) {
  if (!sources?.length) return null;
  return (
    <div className="mt-2 flex flex-wrap gap-1.5">
      <span className="text-[10px] text-fg-faint">sources:</span>
      {sources.map((s, i) => (
        <span key={i} className="rounded border border-brand/30 bg-brand/5 px-1.5 py-0.5 text-[10px] text-fg-dim"
              title={s.doi || s.source_id}>
          {String(s.source_id).split(":").slice(0, 2).join(":")}{s.doi ? ` · ${s.doi}` : ""}
        </span>
      ))}
    </div>
  );
}
function AnglePointers({ angles, onPick }) {
  return (
    <div className="mt-3 rounded-lg border border-brand/25 bg-brand/5 p-2.5">
      <div className="mb-1 text-[11px] font-semibold text-brand"> PEN-STACK can compute a grounded answer:</div>
      <div className="flex flex-col gap-1">
        {angles.map((a, i) => (
          <button key={i} onClick={() => onPick?.(a.example)} className="text-left text-[11px] text-fg-dim hover:text-brand">
            <span className="font-medium">{a.module}</span>, <em>“{a.example}”</em>
          </button>
        ))}
      </div>
    </div>
  );
}

// the dossier shown beneath an answer (compact) and in the rail (full)
function InlineDossier({ d }) {
  return (
    <details className="rounded-xl border border-line bg-ink-900/60 p-3 text-sm" open>
      <summary className="cursor-pointer text-xs font-semibold uppercase tracking-wide text-fg-dim">Grounded dossier</summary>
      <div className="mt-3 space-y-3">
        <VerdictCard verdict={d.verdict} />
        {d.safety?.decision && <SafetyBadge decision={d.safety.decision} reason={d.safety.reason} />}
        {d.immune_profile?.axes && <ImmuneProfileCard profile={d.immune_profile} />}
        <ScopeLedger knownUnknowns={d.immune_profile?.known_unknowns}
                     outOfScope={d.scope?.out_of_scope ? d.scope : null} dense />
      </div>
    </details>
  );
}

function LatestDossier({ msgs, busy }) {
  const last = [...msgs].reverse().find((m) => m.role === "assistant" && m.dossier);
  if (busy) return <Card title="Dossier"><Spinner /></Card>;
  if (!last) return <Card title="Dossier" subtitle="The grounded facts behind the latest answer appear here."><p className="text-xs text-fg-faint">Ask something to see the verdict, safety, immune profile, and scope.</p></Card>;
  const d = last.dossier;
  return (
    <Card title="Dossier" subtitle={`from the engine · narrated by ${last.backend || "deterministic"}`}>
      <div className="space-y-3">
        <VerdictCard verdict={d.verdict} />
        {d.safety?.decision && <SafetyBadge decision={d.safety.decision} reason={d.safety.reason} />}
        {d.immune_profile?.axes && <ImmuneProfileCard profile={d.immune_profile} />}
        <ScopeLedger knownUnknowns={d.immune_profile?.known_unknowns}
                     outOfScope={d.scope?.out_of_scope ? d.scope : null} dense />
      </div>
    </Card>
  );
}

// tiny markdown-ish renderer for **bold**, _italics_, and bullet lines (no number invented, text only)
function Markdownish({ text }) {
  const lines = String(text || "").split("\n");
  return (
    <div className="space-y-1">
      {lines.map((ln, i) => {
        const bullet = /^\s*[•\-]\s+/.test(ln);
        const html = ln
          .replace(/&/g, "&amp;").replace(/</g, "&lt;")
          .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
          .replace(/_([^_]+)_/g, "<em>$1</em>")
          .replace(/`([^`]+)`/g, '<code class="font-mono text-brand">$1</code>')
          .replace(/^\s*[•\-]\s+/, "");
        return <p key={i} className={bullet ? "pl-3 text-fg-dim" : ""} dangerouslySetInnerHTML={{ __html: bullet ? "• " + html : html }} />;
      })}
    </div>
  );
}
