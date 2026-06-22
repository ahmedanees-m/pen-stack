// The app shell: a topbar (brand -> Home + external links + a live grounded/version pill + LLM toggle) and a left
// rail grouped by phase of the loop, with icons. Each tool page gets a consistent header from its nav metadata.
import React, { useEffect, useState } from "react";
import { NavLink, Link, useLocation } from "react-router-dom";
import { GROUPS, NAV } from "../nav.js";
import { api } from "../api.js";
import { Icon } from "./icons.jsx";
import { PageHeader } from "./ui.jsx";

const REPO = "https://github.com/ahmedanees-m/pen-stack";

export default function Layout({ children, backend, allowLlm, setAllowLlm }) {
  const [health, setHealth] = useState(null);
  const [open, setOpen] = useState(false);
  const loc = useLocation();

  useEffect(() => { api.health().then(setHealth).catch(() => setHealth({ status: "down" })); }, []);
  useEffect(() => { setOpen(false); }, [loc.pathname]);

  const up = health?.status === "ok";
  const active = NAV.find((n) => n.path === loc.pathname);
  const isHome = active?.id === "home";

  return (
    <div className="min-h-full">
      {/* Topbar */}
      <header className="sticky top-0 z-30 border-b border-line bg-ink-950/75 backdrop-blur">
        <div className="mx-auto flex h-14 max-w-[1440px] items-center gap-3 px-4">
          <button className="btn-ghost px-2 lg:hidden" onClick={() => setOpen((o) => !o)} aria-label="menu">
            <Icon name="menu" size={18} />
          </button>
          <Link to="/" className="flex items-center gap-2.5 rounded-lg" aria-label="home">
            <span className="grid h-8 w-8 place-items-center rounded-lg bg-brand/15 text-brand"><Icon name="dna" size={18} /></span>
            <div className="leading-tight">
              <div className="text-sm font-semibold tracking-tight">PEN-STACK</div>
              <div className="text-[10.5px] text-fg-faint">genome-writing co-scientist</div>
            </div>
          </Link>

          <div className="ml-auto flex items-center gap-1.5 sm:gap-2">
            <a href={REPO} target="_blank" rel="noreferrer" className="btn-ghost hidden px-2 sm:inline-flex" title="GitHub" aria-label="GitHub"><Icon name="github" size={17} /></a>
            <GroundedPill up={up} backend={backend} version={health?.version} />
            <label className="hidden items-center gap-1.5 text-[11px] text-fg-dim sm:flex" title="Use the local/hosted LLM to narrate; off = deterministic narrator (no LLM)">
              <input type="checkbox" checked={allowLlm} onChange={(e) => setAllowLlm(e.target.checked)} className="accent-[var(--brand)]" />
              LLM narration
            </label>
          </div>
        </div>
      </header>

      <div className="mx-auto flex max-w-[1440px] gap-0">
        {/* Left rail */}
        <aside className={`${open ? "block" : "hidden"} lg:block w-60 shrink-0 border-r border-line px-3 py-4 lg:sticky lg:top-14 lg:h-[calc(100vh-3.5rem)] lg:overflow-y-auto`}>
          {GROUPS.map((g) => (
            <div key={g} className="mb-5">
              <div className="px-2 pb-1.5 text-[10px] font-semibold uppercase tracking-[0.12em] text-fg-faint">{g}</div>
              {NAV.filter((n) => n.group === g).map((n) => (
                <NavLink key={n.path} to={n.path} end={n.path === "/"} title={n.tip}
                  className={({ isActive }) =>
                    `group relative flex items-center gap-2.5 rounded-lg px-2.5 py-1.5 text-sm transition-colors ${
                      isActive ? "bg-brand/12 text-brand" : "text-fg-dim hover:bg-ink-700/50 hover:text-fg"}`}>
                  {({ isActive }) => (
                    <>
                      {isActive && <span className="absolute left-0 top-1.5 h-[calc(100%-12px)] w-0.5 rounded-full bg-brand" />}
                      <Icon name={n.icon} size={16} className={isActive ? "text-brand" : "text-fg-faint group-hover:text-fg-dim"} />
                      {n.label}
                    </>
                  )}
                </NavLink>
              ))}
            </div>
          ))}
          <div className="mt-2 rounded-lg border border-line bg-ink-900/50 px-3 py-2.5 text-[10.5px] leading-relaxed text-fg-faint">
            Decision-support, not a clinical directive. Every number is tool-sourced; what the engine can&apos;t
            compute is listed, never guessed.
          </div>
        </aside>

        {/* Content */}
        <main className="min-w-0 flex-1 px-4 py-6 sm:px-7">
          {!isHome && active && <PageHeader icon={active.icon} title={active.label} subtitle={active.tip} />}
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
      {backend && <span className="hidden text-fg-faint sm:inline">· {backend}</span>}
      {version && <span className="text-fg-faint">· v{version}</span>}
    </span>
  );
}
