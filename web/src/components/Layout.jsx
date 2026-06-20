// The app shell: a topbar (brand + grounded/backend indicator + LLM toggle) and a left-rail nav grouped by phase
// of the loop. The grounded indicator reflects the live engine/health and the last chat backend used.
import React, { useEffect, useState } from "react";
import { NavLink, useLocation } from "react-router-dom";
import { GROUPS, NAV } from "../nav.js";
import { api } from "../api.js";

export default function Layout({ children, backend, allowLlm, setAllowLlm }) {
  const [health, setHealth] = useState(null);
  const [open, setOpen] = useState(false);
  const loc = useLocation();

  useEffect(() => { api.health().then(setHealth).catch(() => setHealth({ status: "down" })); }, []);
  useEffect(() => { setOpen(false); }, [loc.pathname]);

  const up = health?.status === "ok";

  return (
    <div className="min-h-full">
      {/* Topbar */}
      <header className="sticky top-0 z-30 border-b border-line bg-ink-950/80 backdrop-blur">
        <div className="mx-auto flex h-14 max-w-[1400px] items-center gap-3 px-4">
          <button className="btn-ghost px-2 lg:hidden" onClick={() => setOpen((o) => !o)} aria-label="menu">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none"><path d="M4 6h16M4 12h16M4 18h16" stroke="currentColor" strokeWidth="2" strokeLinecap="round" /></svg>
          </button>
          <div className="flex items-center gap-2.5">
            <span className="grid h-8 w-8 place-items-center rounded-lg bg-brand/15 text-brand">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none"><path d="M7 4c4 3 6 5 6 8s-2 5-6 8M17 4c-4 3-6 5-6 8s2 5 6 8" stroke="currentColor" strokeWidth="2" strokeLinecap="round" /></svg>
            </span>
            <div className="leading-tight">
              <div className="text-sm font-semibold tracking-tight">PEN-STACK</div>
              <div className="text-[10.5px] text-fg-faint">genome-writing co-scientist</div>
            </div>
          </div>

          <div className="ml-auto flex items-center gap-2">
            <GroundedPill up={up} backend={backend} version={health?.version} />
            <label className="hidden items-center gap-1.5 text-[11px] text-fg-dim sm:flex" title="Use the local/hosted LLM to narrate; off = deterministic narrator (no LLM)">
              <input type="checkbox" checked={allowLlm} onChange={(e) => setAllowLlm(e.target.checked)} className="accent-[var(--brand)]" />
              LLM narration
            </label>
          </div>
        </div>
      </header>

      <div className="mx-auto flex max-w-[1400px] gap-0">
        {/* Left rail */}
        <aside className={`${open ? "block" : "hidden"} lg:block w-64 shrink-0 border-r border-line px-3 py-4 lg:sticky lg:top-14 lg:h-[calc(100vh-3.5rem)] lg:overflow-y-auto`}>
          {GROUPS.map((g) => (
            <div key={g} className="mb-4">
              <div className="px-2 pb-1 text-[10.5px] font-semibold uppercase tracking-wider text-fg-faint">{g}</div>
              {NAV.filter((n) => n.group === g).map((n) => (
                <NavLink key={n.path} to={n.path} end={n.path === "/"} title={n.tip}
                  className={({ isActive }) =>
                    `group flex flex-col rounded-lg px-2.5 py-1.5 text-sm transition-colors ${
                      isActive ? "bg-brand/15 text-brand" : "text-fg-dim hover:bg-ink-700/50 hover:text-fg"}`}>
                  {n.label}
                </NavLink>
              ))}
            </div>
          ))}
          <div className="px-2 pt-2 text-[10.5px] leading-relaxed text-fg-faint">
            Decision-support, not a clinical directive. Every number is tool-sourced; what the engine can&apos;t
            compute is listed, never guessed.
          </div>
        </aside>

        {/* Content */}
        <main className="min-w-0 flex-1 px-4 py-5 sm:px-6">
          <p className="mb-4 text-xs text-fg-dim">{NAV.find((n) => n.path === loc.pathname)?.tip}</p>
          <div className="fade-in">{children}</div>
        </main>
      </div>
    </div>
  );
}

function GroundedPill({ up, backend, version }) {
  const color = up ? "var(--ok)" : "var(--bad)";
  return (
    <span className="chip" style={{ borderColor: color + "55" }} title={up ? "engine reachable" : "engine unreachable"}>
      <span className="h-1.5 w-1.5 rounded-full" style={{ background: color }} />
      {up ? "grounded" : "engine down"}
      {backend && <span className="text-fg-faint">· {backend}</span>}
      {version && <span className="text-fg-faint">· v{version}</span>}
    </span>
  );
}
